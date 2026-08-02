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
                if self._metadata[process]["base_path"] == base_path
                and self._metadata[process]["compatibility_key"] == compatibility_key
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

        if self.current_size < self.max_size:
            logger.debug("Added new process to the pool")
            self._active.add(lsp_process)
        else:
            logger.debug("Pool is full, skipping process tracking")

        return lsp_process

    async def release(self, process: LSPProcess) -> None:
        """Release a process back to the pool"""
        if process in self._active:
            metadata = self._metadata[process]
            metadata["idle_since"] = asyncio.get_running_loop().time()
            self._active.remove(process)
            self._available.append(process)
            logger.debug("Released process back to pool")
        else:
            # Non-pooled process, just shutdown
            await process.stop()
            # Clean up metadata
            self._metadata.pop(process, None)
            logger.debug("Shutdown non-pooled process")

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
            try:
                await process.stop()
            except Exception as e:
                logger.warning(f"Error shutting down pooled process: {e}")

        logger.debug("Pool cleanup completed")

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
                await self._remove_idle_processes()
        except asyncio.CancelledError:
            pass

    async def _remove_idle_processes(self) -> None:
        """Remove processes that have been idle too long"""
        current_time = asyncio.get_running_loop().time()
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
            self._available.remove(process)
            self._metadata.pop(process, None)
            try:
                await process.stop()
                logger.debug("Removed idle process from pool")
            except Exception as e:
                logger.warning(f"Error shutting down idle process: {e}")
