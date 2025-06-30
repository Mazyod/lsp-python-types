"""
Generic LSP process pool for reusing LSP processes across sessions.
"""

from __future__ import annotations

import asyncio
import logging
import typing as t
from collections import deque

from .process import LSPProcess

logger = logging.getLogger("lsp-types")


class ProcessMetadata(t.TypedDict):
    """Metadata for tracking pooled processes"""

    base_path: str
    created_at: float


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
        self._cleanup_task = asyncio.create_task(self._cleanup_idle_processes())

    @property
    def current_size(self) -> int:
        """Current number of processes in the pool"""
        return len(self._available) + len(self._active)

    @property
    def available_count(self) -> int:
        """Number of available processes in the pool"""
        return len(self._available)

    async def acquire(
        self, process_factory: t.Callable[[], t.Awaitable[LSPProcess]], base_path: str
    ) -> LSPProcess:
        """Acquire a process from the pool or create a new one"""

        # Try to find a compatible available process
        compatible_process = next(
            (p for p in self._available if self._metadata[p]["base_path"] == base_path),
            None,
        )

        if compatible_process:
            self._available.remove(compatible_process)
            self._active.add(compatible_process)
            await self._reset_process(compatible_process, base_path)
            logger.debug("Reusing compatible process from pool")
            return compatible_process

        lsp_process = await process_factory()
        self._metadata[lsp_process] = ProcessMetadata(
            base_path=base_path, created_at=asyncio.get_event_loop().time()
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

        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None

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

    async def _reset_process(self, process: LSPProcess, new_base_path: str) -> None:
        """Reset a process for reuse with new configuration"""
        # Reset the underlying LSP process (handles document cleanup)
        await process.reset()

        metadata = self._metadata[process]

        # Update base path if changed
        if new_base_path != metadata["base_path"]:
            metadata["base_path"] = new_base_path
            # Note: We can't change the rootUri after initialization,
            # but we can update our tracking of it

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
        current_time = asyncio.get_event_loop().time()
        processes_to_remove = []

        for process in self._available:
            metadata = self._metadata[process]
            idle_time = current_time - metadata["created_at"]
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
