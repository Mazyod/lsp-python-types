"""
Tests for LSP client error handling using the mock LSP server.

These tests verify that the LSP client properly handles:
- Timeout when server hangs
- Error responses from server
- Resource cleanup on initialization failure
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from lsp_types import types
from lsp_types.pool import LSPProcessPool
from lsp_types.process import Error, LSPProcess, ProcessLaunchInfo
from lsp_types.session import Session

# Path to the mock LSP server script
MOCK_SERVER_PATH = Path(__file__).parent / "mock_lsp_server.py"


def get_mock_server_cmd(*args: str) -> list[str]:
    """Get the command to launch the mock server with given arguments."""
    return [sys.executable, str(MOCK_SERVER_PATH), *args]


async def test_timeout_when_server_hangs():
    """Test that requests timeout properly when server doesn't respond."""
    # Launch mock server that hangs on hover requests
    launch_info = ProcessLaunchInfo(
        cmd=get_mock_server_cmd("--hang-on", "textDocument/hover"),
    )

    async with LSPProcess(launch_info) as process:
        # Initialize should work normally
        init_result = await process.send.initialize(
            {
                "processId": None,
                "capabilities": {},
                "rootUri": None,
            }
        )
        assert init_result is not None
        assert "capabilities" in init_result

        await process.notify.initialized({})

        # Hover request should timeout since server hangs on it
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                process.send.hover(
                    {
                        "textDocument": {"uri": "file:///test.py"},
                        "position": {"line": 0, "character": 0},
                    }
                ),
                timeout=0.5,  # Short timeout for testing
            )


async def test_error_response_handling():
    """Test that LSP error responses are properly converted to exceptions."""
    # Launch mock server that returns errors on hover requests
    launch_info = ProcessLaunchInfo(
        cmd=get_mock_server_cmd(
            "--error-on",
            "textDocument/hover",
            "--error-code",
            "-32600",
            "--error-message",
            "Test error from mock server",
        ),
    )

    async with LSPProcess(launch_info) as process:
        # Initialize should work normally
        init_result = await process.send.initialize(
            {
                "processId": None,
                "capabilities": {},
                "rootUri": None,
            }
        )
        assert init_result is not None

        await process.notify.initialized({})

        # Hover request should raise an Error exception
        with pytest.raises(Error) as exc_info:
            await process.send.hover(
                {
                    "textDocument": {"uri": "file:///test.py"},
                    "position": {"line": 0, "character": 0},
                }
            )

        error = exc_info.value
        assert error.code == -32600
        assert "Test error from mock server" in str(error)


async def test_shutdown_after_timeout():
    """Test that we can still shutdown cleanly after a request times out."""
    launch_info = ProcessLaunchInfo(
        cmd=get_mock_server_cmd("--hang-on", "textDocument/completion"),
    )

    process = LSPProcess(launch_info)
    await process.start()

    try:
        # Initialize
        await process.send.initialize(
            {
                "processId": None,
                "capabilities": {},
                "rootUri": None,
            }
        )
        await process.notify.initialized({})

        # Request that will timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                process.send.completion(
                    {
                        "textDocument": {"uri": "file:///test.py"},
                        "position": {"line": 0, "character": 0},
                    }
                ),
                timeout=0.3,
            )

        # Should still be able to shutdown cleanly
        # (stop() handles cleanup even after failed requests)
    finally:
        await process.stop()


class FailingBackend:
    """A mock backend that fails during workspace settings retrieval."""

    def __init__(self, fail_on: str = "get_workspace_settings"):
        self.fail_on = fail_on

    def write_config(self, base_path: Path, options: dict) -> None:
        if self.fail_on == "write_config":
            raise RuntimeError("Simulated write_config failure")

    def create_process_launch_info(
        self, base_path: Path, options: dict
    ) -> ProcessLaunchInfo:
        return ProcessLaunchInfo(cmd=get_mock_server_cmd())

    def get_lsp_capabilities(self) -> types.ClientCapabilities:
        return {}

    def get_workspace_settings(
        self, options: dict
    ) -> types.DidChangeConfigurationParams:
        if self.fail_on == "get_workspace_settings":
            raise RuntimeError("Simulated get_workspace_settings failure")
        return {"settings": {}}

    def get_semantic_tokens_legend(self) -> types.SemanticTokensLegend | None:
        return None


async def test_session_create_releases_process_on_failure(tmp_path: Path):
    """Test that Session.create releases the process back to the pool when initialization fails."""
    pool = LSPProcessPool(max_size=2)

    # Create a backend that will fail during get_workspace_settings
    backend = FailingBackend(fail_on="get_workspace_settings")

    try:
        # Attempt to create a session - this should fail
        with pytest.raises(
            RuntimeError, match="Simulated get_workspace_settings failure"
        ):
            await Session.create(
                backend,
                base_path=tmp_path,
                initial_code="x = 1",
                pool=pool,
            )

        # Verify the process was released back to the pool (or shutdown for non-pooled)
        # Since we use max_size=2, the process should be in _available after release
        # But since acquire adds to _active and release moves to _available,
        # after a failed create, the pool should have the process available
        assert pool.current_size == 1, "Process should still be in pool after cleanup"
        assert pool.available_count == 1, "Process should be available after release"
        assert len(pool._active) == 0, "No processes should be active after failure"

    finally:
        await pool.cleanup()


async def test_session_create_cleanup_without_pool(tmp_path: Path):
    """Test that Session.create properly shuts down process when no pool is provided."""
    # Create a backend that will fail during get_workspace_settings
    backend = FailingBackend(fail_on="get_workspace_settings")

    # Track process creation/stop via patching
    original_stop = LSPProcess.stop
    stop_called = []

    async def tracking_stop(self):
        stop_called.append(self)
        return await original_stop(self)

    with patch.object(LSPProcess, "stop", tracking_stop):
        # Attempt to create a session without a pool - this should fail
        with pytest.raises(
            RuntimeError, match="Simulated get_workspace_settings failure"
        ):
            await Session.create(
                backend,
                base_path=tmp_path,
                initial_code="x = 1",
                # No pool provided - uses internal max_size=0 pool
            )

        # Verify process.stop was called (cleanup happened)
        assert len(stop_called) == 1, (
            "Process should be stopped when no pool and creation fails"
        )
