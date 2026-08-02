"""
Generic LSP process pool for reusing LSP processes across sessions.
"""

from __future__ import annotations

import asyncio
import logging
import typing as t
from collections import deque

from .process import LSPProcess, _run_protected

logger = logging.getLogger("lsp-types")


def _now() -> float:
    """Return the current event-loop time.

    Indirection exists so tests can drive pool timing with a manual clock.
    """
    return asyncio.get_running_loop().time()


class ProcessMetadata(t.TypedDict):
    """Metadata for tracking pooled processes"""

    base_path: str
    compatibility_key: t.Hashable | None
    idle_since: t.NotRequired[float]


class LSPProcessPool:
    """Pool for reusing LSP processes across sessions"""

    def __init__(
        self,
        max_size: int = 5,
        max_idle_time: float = 3_600.0,
        cleanup_interval: float = 60.0,
    ):
        self.max_size = max_size
        self._max_idle_time = max_idle_time
        self._cleanup_interval = cleanup_interval
        self._available: deque[LSPProcess] = deque()
        self._active: set[LSPProcess] = set()
        self._metadata: dict[LSPProcess, ProcessMetadata] = {}
        self._cleanup_task: asyncio.Task[None] | None = asyncio.create_task(
            self._cleanup_idle_processes()
        )
        self._cleanup_lock = asyncio.Lock()

    @property
    def current_size(self) -> int:
        """Current number of processes in the pool"""
        return len(self._available) + len(self._active)

    @property
    def available_count(self) -> int:
        """Number of available processes in the pool"""
        return len(self._available)

    async def acquire(
        self,
        process_factory: t.Callable[[], t.Awaitable[LSPProcess]],
        base_path: str,
        *,
        compatibility_key: t.Hashable | None = None,
    ) -> LSPProcess:
        """Acquire a compatible process from the pool or create a new one.

        Callers that omit ``compatibility_key`` retain the original base-path-only
        pooling behavior. Keyed and unkeyed processes are kept separate so callers
        with stronger compatibility requirements never receive an unkeyed process.
        """

        # Try to find a compatible available process
        compatible_process = next(
            (
                process
                for process in self._available
                if self._matches(process, base_path, compatibility_key)
                and process.is_alive
            ),
            None,
        )

        if compatible_process:
            self._available.remove(compatible_process)
            self._active.add(compatible_process)
            self._metadata[compatible_process].pop("idle_since")
            await self._reset_process(compatible_process)
            logger.debug("Reusing compatible process from pool")
            return compatible_process

        lsp_process = await process_factory()
        self._metadata[lsp_process] = ProcessMetadata(
            base_path=base_path,
            compatibility_key=compatibility_key,
        )

        if self.current_size >= self.max_size:
            # Trade-off: a workload strictly alternating between incompatible
            # configurations on a pool smaller than its number of families now
            # evicts and recreates per acquire (equal to never pooling) instead
            # of pinning one family forever. Any max_size >= live families
            # avoids the thrash entirely.
            await self._evict_unusable_idle_process(base_path, compatibility_key)

        if self.current_size < self.max_size:
            logger.debug("Added new process to the pool")
            self._active.add(lsp_process)
        else:
            logger.debug("Pool is full, skipping process tracking")

        return lsp_process

    async def release(self, process: LSPProcess) -> None:
        """Release a process back to the pool.

        A process whose server is gone is dropped instead of pooled: reusing it
        would hand a dead server to the next caller, and because every release
        restarts the idle window, the idle sweep would never expire it either.
        """
        if process not in self._active:
            # Non-pooled process, just shutdown. The pool must forget it even when
            # the shutdown fails, because it is never handed out again either way.
            try:
                await process.stop()
            finally:
                self._metadata.pop(process, None)
            logger.debug("Shutdown non-pooled process")
            return

        self._active.remove(process)

        if not process.is_alive:
            self._metadata.pop(process, None)
            logger.debug("Discarded dead process instead of returning it to the pool")
            await self._stop_quietly(process)
            return

        self._metadata[process]["idle_since"] = _now()
        self._available.append(process)
        logger.debug("Released process back to pool")

    async def discard(self, process: LSPProcess) -> None:
        """Permanently remove a process from the pool and stop it.

        Used for processes that must never be leased again — for example one
        whose session shut down while an operation was still borrowing it,
        because that operation's queued writes would otherwise interleave with
        the next session's protocol stream.
        """
        # Bookkeeping is dropped before the process is stopped so a failing or
        # cancelled stop can never leave a dead process visible to acquire().
        self._active.discard(process)
        if process in self._available:
            self._available.remove(process)
        self._metadata.pop(process, None)

        await self._stop_quietly(process)
        logger.debug("Discarded process from pool")

    async def cleanup(self) -> None:
        """Clean up all processes in the pool"""
        async with self._cleanup_lock:
            await _run_protected(self._cleanup_resources())

    async def _cleanup_resources(self) -> None:
        """Join the maintenance worker and stop every process owned by the pool."""
        # Cancel cleanup task
        cleanup_task = self._cleanup_task
        if cleanup_task is not None:
            self._cleanup_task = None
            cleanup_task.cancel()
            [worker_result] = await asyncio.gather(cleanup_task, return_exceptions=True)
            if isinstance(worker_result, Exception):
                logger.warning("Pool cleanup worker failed: %s", worker_result)

        # Shutdown all processes
        all_processes = list(self._available) + list(self._active)
        # Clear the pools eagerly to avoid race conditions
        self._available.clear()
        self._active.clear()
        self._metadata.clear()

        for process in all_processes:
            await self._stop_quietly(process)

        logger.debug("Pool cleanup completed")

    def _matches(
        self,
        process: LSPProcess,
        base_path: str,
        compatibility_key: t.Hashable | None,
    ) -> bool:
        """Whether an owned process was initialized for exactly these inputs."""
        metadata = self._metadata[process]
        return (
            metadata["base_path"] == base_path
            and metadata["compatibility_key"] == compatibility_key
        )

    def _claim_available(self, process: LSPProcess) -> bool:
        """Take an available process out of the pool without yielding control.

        Returns False when a concurrent acquire already checked the process out.
        The caller owns the process once this returns True and must stop it.
        """
        if process not in self._available:
            return False

        self._available.remove(process)
        self._metadata.pop(process, None)
        return True

    def _is_idle_expired(self, process: LSPProcess, current_time: float) -> bool:
        """Whether the process is still idle past its deadline at ``current_time``."""
        metadata = self._metadata.get(process)
        idle_since = metadata.get("idle_since") if metadata else None
        return (
            idle_since is not None and current_time - idle_since > self._max_idle_time
        )

    async def _stop_quietly(self, process: LSPProcess) -> None:
        """Stop a pool-owned process, logging rather than propagating failures."""
        try:
            await process.stop()
        except Exception as e:
            logger.warning(f"Error shutting down pooled process: {e}")

    async def _evict_unusable_idle_process(
        self, base_path: str, compatibility_key: t.Hashable | None
    ) -> bool:
        """Free a slot by stopping the longest-idle process this request cannot use.

        Only available processes are eligible: an active process is still leased by
        a caller. Returns True when a slot was freed.
        """
        candidate = min(
            (
                process
                for process in self._available
                if not self._matches(process, base_path, compatibility_key)
                or not process.is_alive
            ),
            # Dead candidates first: a corpse must never keep its slot while a
            # live (merely non-matching) server is stopped in its place.
            key=lambda process: (
                process.is_alive,
                self._metadata[process].get("idle_since", 0.0),
            ),
            default=None,
        )
        if candidate is None or not self._claim_available(candidate):
            return False

        logger.debug("Evicted unusable idle process to free a pool slot")
        await self._stop_quietly(candidate)
        return True

    async def _reset_process(self, process: LSPProcess) -> None:
        """Reset a process for reuse.

        Note: This method is only called after acquire() has already filtered
        for processes with a matching base_path. The rootUri is set at LSP
        initialization and cannot be changed, so we only reuse processes
        with the same base_path.
        """
        # Reset the underlying LSP process (handles document cleanup)
        await process.reset()

    async def _cleanup_idle_processes(self) -> None:
        """Background task to clean up idle processes"""
        try:
            while True:
                await asyncio.sleep(self._cleanup_interval)
                try:
                    await self._remove_idle_processes()
                except Exception as e:
                    logger.warning(f"Idle process sweep failed: {e}")
        except asyncio.CancelledError:
            pass

    async def _remove_idle_processes(self) -> None:
        """Remove processes that have been idle too long"""
        current_time = _now()
        processes_to_remove = []

        for process in self._available:
            metadata = self._metadata[process]
            idle_since = metadata.get("idle_since")
            if idle_since is None:
                raise RuntimeError("Available process is missing an idle timestamp")
            idle_time = current_time - idle_since
            if idle_time > self._max_idle_time:
                processes_to_remove.append(process)

        for process in processes_to_remove:
            # Stopping an earlier candidate suspends this sweep, so re-check the
            # process against live pool state: a concurrent acquire may have
            # checked it out, or checked it out and returned it with a fresh idle
            # window. Both checks run without awaiting so acquire cannot
            # interleave between them.
            if not self._is_idle_expired(process, current_time):
                continue
            if not self._claim_available(process):
                continue

            await self._stop_quietly(process)
            logger.debug("Removed idle process from pool")
