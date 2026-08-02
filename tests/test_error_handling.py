"""
Tests for LSP client error handling using the mock LSP server.

These tests verify that the LSP client properly handles:
- Timeout when server hangs
- Error responses from server
- Resource cleanup on initialization failure
"""

from __future__ import annotations

import asyncio
import signal
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import lsp_types.process as process_module
from lsp_types import types
from lsp_types.pool import LSPProcessPool
from lsp_types.process import Error, LSPProcess, ProcessLaunchInfo, _run_protected
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
        assert process.initialize_result == init_result

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


@pytest.mark.skipif(sys.platform == "win32", reason="uses POSIX process signals")
async def test_stop_times_out_hung_shutdown_and_reaps_process(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    """A server that ignores shutdown cannot block cleanup or remain alive."""
    monkeypatch.setattr(process_module, "_GRACEFUL_SHUTDOWN_TIMEOUT", 0.05)
    monkeypatch.setattr(process_module, "_PROCESS_EXIT_TIMEOUT", 0.05)
    process = LSPProcess(
        ProcessLaunchInfo(
            cmd=get_mock_server_cmd("--hang-on", "shutdown", "--ignore-sigterm")
        )
    )
    await process.start()
    await process.send.initialize(
        {"processId": None, "capabilities": {}, "rootUri": None}
    )
    subprocess = process._process
    assert subprocess is not None

    await asyncio.wait_for(process.stop(), timeout=1.0)

    assert process._process is None
    assert subprocess.returncode == -signal.SIGKILL
    assert not process._tasks
    assert not process._pending_requests
    assert "did not terminate; killing process" in caplog.text


@pytest.mark.skipif(sys.platform == "win32", reason="uses POSIX process signals")
async def test_cancelled_stop_finishes_reaping_before_propagating(
    monkeypatch: pytest.MonkeyPatch,
):
    """Caller cancellation cannot interrupt subprocess reaping."""
    monkeypatch.setattr(process_module, "_GRACEFUL_SHUTDOWN_TIMEOUT", 0.05)
    monkeypatch.setattr(process_module, "_PROCESS_EXIT_TIMEOUT", 0.05)
    process = LSPProcess(
        ProcessLaunchInfo(
            cmd=get_mock_server_cmd("--hang-on", "shutdown", "--ignore-sigterm")
        )
    )
    await process.start()
    await process.send.initialize(
        {"processId": None, "capabilities": {}, "rootUri": None}
    )
    subprocess = process._process
    assert subprocess is not None

    terminate_wait_started = asyncio.Event()
    original_wait_for_exit = process._wait_for_exit

    async def tracked_wait_for_exit(
        child: asyncio.subprocess.Process, timeout: float
    ) -> bool:
        terminate_wait_started.set()
        return await original_wait_for_exit(child, timeout)

    monkeypatch.setattr(process, "_wait_for_exit", tracked_wait_for_exit)
    stop_task = asyncio.create_task(process.stop())
    await asyncio.wait_for(terminate_wait_started.wait(), timeout=1.0)
    stop_task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await stop_task

    assert subprocess.returncode == -signal.SIGKILL
    assert process._process is None
    assert not process._tasks
    assert not process._pending_requests


async def test_completed_notification_tasks_are_not_retained(
    monkeypatch: pytest.MonkeyPatch,
):
    """Fire-and-forget notifications leave the internal task registry promptly."""
    process = LSPProcess(ProcessLaunchInfo(cmd=get_mock_server_cmd()))
    await process.start()
    release_notifications = asyncio.Event()
    all_notifications_started = asyncio.Event()
    notifications_started = 0
    original_send_payload = process._send_payload

    async def gated_send_payload(stream, payload):  # type: ignore[no-untyped-def]
        nonlocal notifications_started
        if payload.get("method") == "initialized":
            notifications_started += 1
            if notifications_started == 100:
                all_notifications_started.set()
            await release_notifications.wait()
        await original_send_payload(stream, payload)

    monkeypatch.setattr(process, "_send_payload", gated_send_payload)
    notifications = [process.notify.initialized({}) for _ in range(100)]

    try:
        await asyncio.wait_for(all_notifications_started.wait(), timeout=1.0)
        assert len(process._tasks) == 102

        release_notifications.set()
        await asyncio.gather(*notifications)
        await asyncio.sleep(0)

        assert len(process._tasks) == 2
    finally:
        release_notifications.set()
        await asyncio.gather(*notifications, return_exceptions=True)
        await process.stop()

    assert not process._tasks


async def test_task_cleanup_drains_tasks_added_during_cancellation():
    """Tasks created while cancellation is unwinding remain owned and are joined."""
    process = LSPProcess(ProcessLaunchInfo(cmd=get_mock_server_cmd()))
    late_tasks: list[asyncio.Task[None]] = []

    async def wait_forever() -> None:
        await asyncio.Event().wait()

    async def add_late_task_during_cleanup() -> None:
        try:
            await asyncio.Event().wait()
        finally:
            late_task = process._track_task(asyncio.create_task(wait_forever()))
            late_tasks.append(late_task)

    process._track_task(asyncio.create_task(add_late_task_during_cleanup()))
    await asyncio.sleep(0)

    await process._cancel_tasks()

    assert len(late_tasks) == 1
    assert late_tasks[0].cancelled()
    assert not process._tasks


async def test_concurrent_stop_calls_share_cleanup(monkeypatch: pytest.MonkeyPatch):
    """Concurrent callers can safely wait for one idempotent cleanup."""
    process = LSPProcess(ProcessLaunchInfo(cmd=get_mock_server_cmd()))
    await process.start()
    shutdown_count = 0
    original_request_graceful_shutdown = process._request_graceful_shutdown

    async def counted_graceful_shutdown() -> bool:
        nonlocal shutdown_count
        shutdown_count += 1
        return await original_request_graceful_shutdown()

    monkeypatch.setattr(
        process, "_request_graceful_shutdown", counted_graceful_shutdown
    )

    await asyncio.gather(process.stop(), process.stop())

    assert shutdown_count == 1
    assert process._process is None
    assert not process._tasks


async def test_stopped_process_cannot_restart():
    """Stopping is a terminal lifecycle transition."""
    process = LSPProcess(ProcessLaunchInfo(cmd=get_mock_server_cmd()))
    await process.start()
    await process.stop()

    with pytest.raises(RuntimeError, match="cannot be restarted"):
        await process.start()


async def test_start_and_stop_are_serialized(monkeypatch: pytest.MonkeyPatch):
    """Stopping during startup cannot publish a process after terminal shutdown."""
    process = LSPProcess(ProcessLaunchInfo(cmd=get_mock_server_cmd()))
    spawn_started = asyncio.Event()
    allow_spawn = asyncio.Event()
    original_create_subprocess_exec = asyncio.create_subprocess_exec

    async def gated_create_subprocess_exec(*args, **kwargs):  # type: ignore[no-untyped-def]
        spawn_started.set()
        await allow_spawn.wait()
        return await original_create_subprocess_exec(*args, **kwargs)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", gated_create_subprocess_exec)
    start_task = asyncio.create_task(process.start())
    await asyncio.wait_for(spawn_started.wait(), timeout=1.0)
    stop_task = asyncio.create_task(process.stop())
    await asyncio.sleep(0)

    assert not stop_task.done()

    allow_spawn.set()
    await start_task
    await stop_task

    assert process._process is None
    assert process._stopped
    assert not process._tasks


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

    def requires_file_on_disk(self) -> bool:
        return False

    def consumes_did_change_configuration(self) -> bool:
        return True


class MockBackend:
    """Backend that talks to the mock LSP server, with a configurable predicate."""

    def __init__(self, *, consumes_config: bool):
        self._consumes_config = consumes_config

    def write_config(self, base_path: Path, options: dict) -> None:
        return None

    def create_process_launch_info(
        self, base_path: Path, options: dict
    ) -> ProcessLaunchInfo:
        return ProcessLaunchInfo(cmd=get_mock_server_cmd())

    def get_lsp_capabilities(self) -> types.ClientCapabilities:
        return {}

    def get_workspace_settings(
        self, options: dict
    ) -> types.DidChangeConfigurationParams:
        return {"settings": {}}

    def get_semantic_tokens_legend(self) -> types.SemanticTokensLegend | None:
        return None

    def requires_file_on_disk(self) -> bool:
        return False

    def consumes_did_change_configuration(self) -> bool:
        return self._consumes_config


async def _capture_session_notifications(
    backend: MockBackend, tmp_path: Path
) -> list[str]:
    """Run Session.create against `backend` and return the methods it notified."""
    captured: list[str] = []
    real_send = LSPProcess._send_notification

    async def recording_send(self, method: str, params):  # type: ignore[no-untyped-def]
        captured.append(method)
        return await real_send(self, method, params)

    with patch.object(LSPProcess, "_send_notification", recording_send):
        session = await Session.create(
            backend, base_path=tmp_path, initial_code="x = 1"
        )
        await session.shutdown()
    return captured


async def test_did_change_configuration_gate(tmp_path: Path):
    """The notification is sent iff the backend predicate returns True."""
    sent = await _capture_session_notifications(
        MockBackend(consumes_config=True), tmp_path
    )
    assert "workspace/didChangeConfiguration" in sent

    skipped = await _capture_session_notifications(
        MockBackend(consumes_config=False), tmp_path
    )
    assert "workspace/didChangeConfiguration" not in skipped


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


async def test_run_protected_defers_caller_cancellation():
    """Cancelling the caller cannot interrupt protected cleanup work."""
    started = asyncio.Event()
    allow_finish = asyncio.Event()
    finished = False

    async def cleanup() -> None:
        nonlocal finished
        started.set()
        await allow_finish.wait()
        finished = True

    runner = asyncio.create_task(_run_protected(cleanup()))
    await asyncio.wait_for(started.wait(), timeout=1.0)
    runner.cancel()
    await asyncio.sleep(0)

    assert not runner.done()
    assert not finished

    allow_finish.set()
    with pytest.raises(asyncio.CancelledError):
        await runner

    assert finished
