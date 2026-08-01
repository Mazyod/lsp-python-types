"""
Tests for session pool functionality.
"""

import asyncio
import logging
import tempfile
import time
import typing as t
from pathlib import Path

import pytest

import lsp_types
from lsp_types.pool import LSPProcessPool
from lsp_types.process import LSPProcess, ProcessLaunchInfo
from lsp_types.pyrefly.backend import PyreflyBackend
from lsp_types.pyright.backend import PyrightBackend
from lsp_types.session import (
    _build_process_compatibility_key,
    _freeze_for_compatibility,
)
from lsp_types.ty.backend import TyBackend
from lsp_types.zuban.backend import ZubanBackend


@pytest.fixture(params=[PyrightBackend, PyreflyBackend, TyBackend, ZubanBackend])
def lsp_backend(request):
    """Parametrized fixture providing Pyright, Pyrefly, ty, and Zuban backends"""
    return request.param()


@pytest.fixture
def backend_name(lsp_backend):
    """Helper fixture to get the backend name for test identification"""
    return lsp_backend.__class__.__name__.replace("Backend", "").lower()


class _StubLSPProcess(LSPProcess):
    def __init__(self) -> None:
        super().__init__(ProcessLaunchInfo(cmd=["stub-lsp-process"]))
        self.reset_count = 0
        self.stop_count = 0

    async def reset(self) -> None:
        self.reset_count += 1

    async def stop(self) -> None:
        self.stop_count += 1


class _ManualClock:
    def __init__(self) -> None:
        self.current_time = 0.0

    def time(self) -> float:
        return self.current_time

    def advance(self, seconds: float) -> None:
        self.current_time += seconds


async def _unexpected_process_factory() -> LSPProcess:
    raise AssertionError("Expected the available process to be reused")


def test_compatibility_values_are_structural_and_type_safe():
    """Equivalent mappings match without conflating distinct scalar types."""
    left = {"nested": {"first": True, "second": [1, "1"]}, "other": None}
    right = {"other": None, "nested": {"second": [1, "1"], "first": True}}

    assert _freeze_for_compatibility(left) == _freeze_for_compatibility(right)
    assert _freeze_for_compatibility(True) != _freeze_for_compatibility(1)
    assert _freeze_for_compatibility(1) != _freeze_for_compatibility(1.0)
    assert _freeze_for_compatibility(0.0) != _freeze_for_compatibility(-0.0)

    class UnsupportedValue:
        pass

    unsupported = UnsupportedValue()
    assert _freeze_for_compatibility(unsupported) != _freeze_for_compatibility(
        unsupported
    )


def test_process_compatibility_key_includes_all_launch_inputs(tmp_path: Path):
    """Command, effective environment, and cwd each partition process families."""
    backend = PyrightBackend()
    initialize_params: lsp_types.InitializeParams = {
        "processId": None,
        "rootUri": f"file://{tmp_path}",
        "capabilities": {},
    }

    def build_key(
        *,
        command: list[str] | None = None,
        environment: dict[str, str] | None = None,
        cwd: Path | None = None,
    ):
        return _build_process_compatibility_key(
            backend,
            base_path=str(tmp_path),
            process_launch_info=ProcessLaunchInfo(
                cmd=command or ["language-server", "--stdio"],
                cwd=cwd or tmp_path,
            ),
            resolved_environment=environment or {"PATH": "/bin"},
            options={},
            initialize_params=initialize_params,
        )

    baseline = build_key()
    assert baseline != build_key(command=["other-server", "--stdio"])
    assert baseline != build_key(environment={"PATH": "/other-bin"})
    assert baseline != build_key(cwd=tmp_path / "other-workspace")


class TestLSPProcessPool:
    """Test session pool functionality"""

    @pytest.fixture
    async def session_pool(self):
        """Create a session pool for testing"""
        pool = LSPProcessPool(max_size=3)
        yield pool
        await pool.cleanup()

    @pytest.fixture
    async def idle_pool(self, monkeypatch: pytest.MonkeyPatch):
        """Create an active stub process governed by a manual monotonic clock."""
        clock = _ManualClock()
        monkeypatch.setattr(asyncio, "get_running_loop", lambda: clock)
        pool = LSPProcessPool(max_idle_time=10.0, cleanup_interval=3_600.0)
        process = _StubLSPProcess()

        async def create_process() -> LSPProcess:
            return process

        acquired = await pool.acquire(create_process, "/workspace")
        yield pool, clock, acquired
        await pool.cleanup()

    @pytest.fixture
    def base_path(self, tmp_path: Path) -> Path:
        """Provide a temp directory as base_path for sessions"""
        return tmp_path

    async def test_session_pool_creation(self, session_pool):
        """Test that session pool can be created with proper configuration"""
        assert session_pool.max_size == 3
        assert session_pool.current_size == 0
        assert session_pool.available_count == 0

    async def test_acquire_selects_by_optional_compatibility_key(self):
        """Keys isolate process families while omitted keys retain legacy reuse."""
        pool = LSPProcessPool(max_size=4)
        created: list[_StubLSPProcess] = []

        async def create_process() -> LSPProcess:
            process = _StubLSPProcess()
            created.append(process)
            return process

        try:
            first = await pool.acquire(
                create_process,
                "/workspace",
                compatibility_key=("backend", "pyright"),
            )
            await pool.release(first)

            reused = await pool.acquire(
                create_process,
                "/workspace",
                compatibility_key=("backend", "pyright"),
            )
            assert reused is first
            assert created[0].reset_count == 1
            await pool.release(reused)

            incompatible = await pool.acquire(
                create_process,
                "/workspace",
                compatibility_key=("backend", "pyrefly"),
            )
            assert incompatible is not first
            await pool.release(incompatible)

            legacy = await pool.acquire(create_process, "/workspace")
            assert legacy not in (first, incompatible)
            await pool.release(legacy)
            legacy_reused = await pool.acquire(create_process, "/workspace")
            assert legacy_reused is legacy
            assert len(created) == 3
            await pool.release(legacy_reused)
        finally:
            await pool.cleanup()

    async def test_idle_timeout_starts_when_active_process_is_released(self, idle_pool):
        """Time spent actively leased does not count toward the idle timeout."""
        pool, clock, process = idle_pool
        clock.advance(100.0)
        await pool.release(process)
        await pool._remove_idle_processes()

        assert pool.available_count == 1
        assert process.stop_count == 0

    async def test_releasing_reacquired_process_resets_idle_timeout(self, idle_pool):
        """Every return to the pool starts a fresh idle window."""
        pool, clock, process = idle_pool
        await pool.release(process)
        clock.advance(8.0)

        second_lease = await pool.acquire(_unexpected_process_factory, "/workspace")
        clock.advance(100.0)
        await pool.release(second_lease)
        clock.advance(9.0)
        await pool._remove_idle_processes()

        assert pool.available_count == 1
        assert process.reset_count == 1
        assert process.stop_count == 0

    async def test_idle_process_expires_after_release_timeout(self, idle_pool):
        """A genuinely idle process is stopped after its idle window."""
        pool, clock, process = idle_pool
        await pool.release(process)
        clock.advance(10.0)
        await pool._remove_idle_processes()

        assert pool.available_count == 1
        assert process.stop_count == 0

        clock.advance(1.0)
        await pool._remove_idle_processes()

        assert pool.current_size == 0
        assert process.stop_count == 1

    async def test_cleanup_awaits_inflight_idle_cleanup(self):
        """Pool cleanup joins its worker before returning."""
        stop_started = asyncio.Event()
        allow_stop = asyncio.Event()
        stop_finished = asyncio.Event()

        class BlockingStopProcess(_StubLSPProcess):
            async def stop(self) -> None:
                self.stop_count += 1
                stop_started.set()
                try:
                    await allow_stop.wait()
                finally:
                    stop_finished.set()

        pool = LSPProcessPool(max_idle_time=0.0, cleanup_interval=0.01)
        process = BlockingStopProcess()

        async def create_process() -> LSPProcess:
            return process

        try:
            acquired = await pool.acquire(create_process, "/workspace")
            await pool.release(acquired)
            await asyncio.wait_for(stop_started.wait(), timeout=1.0)

            await pool.cleanup()

            assert stop_finished.is_set()
            assert process.stop_count == 1
        finally:
            allow_stop.set()
            await pool.cleanup()

    async def test_cancelled_cleanup_stops_every_owned_process(self):
        """Caller cancellation is propagated only after all processes stop."""
        stop_started = asyncio.Event()
        allow_stop = asyncio.Event()

        class BlockingStopProcess(_StubLSPProcess):
            async def stop(self) -> None:
                self.stop_count += 1
                stop_started.set()
                await allow_stop.wait()

        pool = LSPProcessPool(max_size=2, cleanup_interval=3_600.0)
        processes = [BlockingStopProcess(), BlockingStopProcess()]

        async def create_first() -> LSPProcess:
            return processes[0]

        async def create_second() -> LSPProcess:
            return processes[1]

        try:
            await pool.acquire(create_first, "/workspace/one")
            await pool.acquire(create_second, "/workspace/two")
            cleanup_task = asyncio.create_task(pool.cleanup())
            await asyncio.wait_for(stop_started.wait(), timeout=1.0)
            cleanup_task.cancel()
            await asyncio.sleep(0)

            assert not cleanup_task.done()

            allow_stop.set()
            with pytest.raises(asyncio.CancelledError):
                await cleanup_task

            assert [process.stop_count for process in processes] == [1, 1]
            assert pool.current_size == 0
        finally:
            allow_stop.set()
            await pool.cleanup()

    async def test_cleanup_continues_after_worker_failure(
        self, caplog: pytest.LogCaptureFixture
    ):
        """A failed maintenance worker cannot prevent foreground cleanup."""
        pool = LSPProcessPool(cleanup_interval=3_600.0)
        process = _StubLSPProcess()

        async def create_process() -> LSPProcess:
            return process

        original_worker = pool._cleanup_task
        assert original_worker is not None
        original_worker.cancel()
        await asyncio.gather(original_worker, return_exceptions=True)

        async def fail_worker() -> None:
            raise RuntimeError("simulated cleanup worker failure")

        pool._cleanup_task = asyncio.create_task(fail_worker())
        await asyncio.sleep(0)
        await pool.acquire(create_process, "/workspace")

        await pool.cleanup()

        assert process.stop_count == 1
        assert pool.current_size == 0
        assert "simulated cleanup worker failure" in caplog.text

    async def test_sessions_with_different_backends_do_not_share_processes(
        self, session_pool, base_path
    ):
        """A process initialized as one backend cannot serve another backend."""
        pyright_session = await lsp_types.Session.create(
            PyrightBackend(),
            base_path=base_path,
            initial_code="x = 1",
            pool=session_pool,
        )
        await pyright_session.shutdown()

        pyrefly_session = await lsp_types.Session.create(
            PyreflyBackend(),
            base_path=base_path,
            initial_code="x = 1",
            pool=session_pool,
        )
        try:
            assert session_pool.current_size == 2
            server_info = pyrefly_session.server_info
            assert server_info is not None
            assert "pyrefly" in server_info["name"].lower()
        finally:
            await pyrefly_session.shutdown()

    async def test_session_pool_acquire_and_recycle(
        self, session_pool, lsp_backend, base_path
    ):
        """Test basic session acquisition and recycling"""
        # Create a session using the pool
        session = await lsp_types.Session.create(
            lsp_backend, base_path=base_path, initial_code="x = 1", pool=session_pool
        )

        # Verify session works
        hover_info = await session.get_hover_info(
            lsp_types.Position(line=0, character=0)
        )
        assert hover_info is not None

        # Recycle the session
        await session.shutdown()

        # Pool should now have one available session
        assert session_pool.available_count == 1
        assert session_pool.current_size == 1

    async def test_session_recycling_with_different_code(
        self, session_pool, lsp_backend, base_path
    ):
        """Test that recycled sessions work correctly with different code"""
        # First session with initial code
        session1 = await lsp_types.Session.create(
            lsp_backend,
            base_path=base_path,
            initial_code="def func1(): pass",
            pool=session_pool,
        )

        # Check that the function exists
        hover_info = await session1.get_hover_info(
            lsp_types.Position(line=0, character=4)
        )
        assert hover_info is not None
        assert "func1" in str(hover_info)

        await session1.shutdown()

        # Second session with different code - should reuse the recycled session
        session2 = await lsp_types.Session.create(
            lsp_backend,
            base_path=base_path,
            initial_code="def func2(): pass",
            pool=session_pool,
        )

        # Verify the session was recycled (same pool, different code)
        assert session_pool.current_size == 1  # Still only one process

        # Check that the new function exists and old one doesn't cause issues
        hover_info = await session2.get_hover_info(
            lsp_types.Position(line=0, character=4)
        )
        assert hover_info is not None
        assert "func2" in str(hover_info)

        await session2.shutdown()

    async def test_session_recycling_with_different_options(
        self, session_pool, lsp_backend, backend_name, base_path
    ):
        """Sessions with different options do not reuse initialized processes."""

        options1: t.Mapping[str, t.Any]
        options2: t.Mapping[str, t.Any]
        if backend_name == "pyright":
            from lsp_types.pyright.config_schema import Model as ConfigType

            options1 = ConfigType(strict=["reportUndefinedVariable"])
            options2 = ConfigType(strict=["reportGeneralTypeIssues"])
            code1 = "undefined_var = 1"
            code2 = "x: int = 'string'"  # Type error
        else:  # pyrefly
            from lsp_types.pyrefly.config_schema import Model as ConfigType

            options1 = ConfigType(verbose=True, threads=1)
            options2 = ConfigType(verbose=False, threads=2)
            code1 = "test_var = 1"
            code2 = "x: int = 42"

        # First session with first options
        session1 = await lsp_types.Session.create(
            lsp_backend,
            base_path=base_path,
            initial_code=code1,
            options=options1,
            pool=session_pool,
        )

        await session1.shutdown()

        # Second session with different options must use a separately initialized process
        session2 = await lsp_types.Session.create(
            lsp_backend,
            base_path=base_path,
            initial_code=code2,
            options=options2,
            pool=session_pool,
        )

        assert session_pool.current_size == 2

        # Warm up the session with new code
        await session2.update_code(code2)

        await session2.shutdown()

    async def test_sessions_with_different_initialize_params_do_not_share_processes(
        self, session_pool, base_path
    ):
        """Initialization inputs are part of process compatibility."""

        def initialize_params(client_name: str) -> lsp_types.InitializeParams:
            return {
                "processId": None,
                "rootUri": f"file://{base_path}",
                "capabilities": {},
                "clientInfo": {"name": client_name},
            }

        first = await lsp_types.Session.create(
            PyrightBackend(),
            base_path=base_path,
            initial_code="x = 1",
            initialize_params=initialize_params("first-client"),
            pool=session_pool,
        )
        await first.shutdown()

        second = await lsp_types.Session.create(
            PyrightBackend(),
            base_path=base_path,
            initial_code="x = 1",
            initialize_params=initialize_params("second-client"),
            pool=session_pool,
        )
        try:
            assert session_pool.current_size == 2
        finally:
            await second.shutdown()

    async def test_session_pool_max_size_limit(
        self, session_pool, lsp_backend, base_path
    ):
        """Test that pool respects max size limit"""
        sessions = []

        # Create sessions up to max size
        for i in range(session_pool.max_size):
            session = await lsp_types.Session.create(
                lsp_backend,
                base_path=base_path,
                initial_code=f"x{i} = {i}",
                pool=session_pool,
            )
            sessions.append(session)

        # All sessions should be created
        assert session_pool.current_size == 3

        # Try to create one more session - should create a new process (not pooled)
        extra_session = await lsp_types.Session.create(
            lsp_backend,
            base_path=base_path,
            initial_code="extra = 999",
            pool=session_pool,
        )
        sessions.append(extra_session)

        # Pool size should still be at max, but we have 4 active sessions
        assert session_pool.current_size == 3

        # Clean up all sessions
        for session in sessions:
            await session.shutdown()

    async def test_concurrent_session_usage(self, session_pool, lsp_backend, base_path):
        """Test concurrent session acquisition and usage"""

        async def use_session(session_id: int):
            session = await lsp_types.Session.create(
                lsp_backend,
                base_path=base_path,
                initial_code=f"def func_{session_id}(): return {session_id}",
                pool=session_pool,
            )

            # Do some work with the session
            hover_info = await session.get_hover_info(
                lsp_types.Position(line=0, character=4)
            )
            assert hover_info is not None

            # Update code to test session isolation
            await session.update_code(f"result_{session_id} = func_{session_id}()")

            await session.shutdown()
            return session_id

        # Run multiple sessions concurrently
        tasks = [use_session(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # All sessions should have completed successfully
        assert results == list(range(5))

        # Pool should have recycled sessions available
        assert session_pool.available_count > 0

    async def test_session_warmup_on_recycle(
        self, session_pool, lsp_backend, backend_name, base_path
    ):
        """Test that recycled sessions are properly warmed up with new code"""
        # ty hover doesn't include variable names (shows only type)
        if backend_name == "ty":
            pytest.xfail("ty hover doesn't include variable names in output")

        # Create session with initial code
        session1 = await lsp_types.Session.create(
            lsp_backend,
            base_path=base_path,
            initial_code="old_var = 'old_value'",
            pool=session_pool,
        )

        # Verify old code is present
        hover_info = await session1.get_hover_info(
            lsp_types.Position(line=0, character=0)
        )
        assert hover_info is not None
        assert "old_var" in str(hover_info)

        await session1.shutdown()

        # Create new session with different code
        new_code = "new_var = 'new_value'"
        session2 = await lsp_types.Session.create(
            lsp_backend,
            base_path=base_path,
            initial_code=new_code,
            pool=session_pool,
        )

        # Verify new code is present and old code is gone
        hover_info = await session2.get_hover_info(
            lsp_types.Position(line=0, character=0)
        )
        assert hover_info is not None
        assert "new_var" in str(hover_info)

        # Old variable should not be accessible
        diagnostics = await session2.get_diagnostics()
        # Update code to reference old variable - should cause error
        await session2.update_code("print(old_var)")
        diagnostics = await session2.get_diagnostics()

        # Should have error about undefined variable
        assert len(diagnostics) > 0
        assert any("old_var" in diag.get("message", "") for diag in diagnostics)

        await session2.shutdown()

    async def test_session_pool_cleanup(self, session_pool, lsp_backend, base_path):
        """Test proper cleanup of session pool resources"""
        # Create and recycle a session
        session = await lsp_types.Session.create(
            lsp_backend,
            base_path=base_path,
            initial_code="test_var = 42",
            pool=session_pool,
        )
        await session.shutdown()

        # Pool should have one available session
        assert session_pool.available_count == 1
        assert session_pool.current_size == 1

        # Cleanup the pool
        await session_pool.cleanup()

        # Pool should be empty
        assert session_pool.available_count == 0
        assert session_pool.current_size == 0

    async def test_session_pool_with_temp_directory(self, lsp_backend):
        """Test session pool works with temporary directories"""
        pool = LSPProcessPool(max_size=2)

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Create a module in the temp directory
                module_path = temp_path / "mymodule"
                module_path.mkdir()

                utils_file = module_path / "utils.py"
                utils_file.write_text("def helper(): return 'help'")
                module_path.joinpath("__init__.py").touch()

                # First session
                session1 = await lsp_types.Session.create(
                    lsp_backend,
                    base_path=temp_path,
                    initial_code="from mymodule.utils import helper\nresult = helper()",
                    pool=pool,
                )

                diagnostics = await session1.get_diagnostics()
                assert len(diagnostics) == 0  # No import errors

                await session1.shutdown()

                # Second session with same base path
                session2 = await lsp_types.Session.create(
                    lsp_backend,
                    base_path=temp_path,
                    initial_code="from mymodule.utils import helper\nprint(helper())",
                    pool=pool,
                )

                diagnostics = await session2.get_diagnostics()
                assert len(diagnostics) == 0  # No import errors

                await session2.shutdown()

        finally:
            await pool.cleanup()

    async def test_pool_exhaustion_fallback(self, session_pool, lsp_backend, base_path):
        """Test that pool exhaustion gracefully falls back to new sessions"""
        # Fill up the pool
        active_sessions = []
        for i in range(session_pool.max_size):
            session = await lsp_types.Session.create(
                lsp_backend,
                base_path=base_path,
                initial_code=f"x{i} = {i}",
                pool=session_pool,
            )
            active_sessions.append(session)

        # Pool should be at capacity
        assert session_pool.current_size == session_pool.max_size
        assert session_pool.available_count == 0

        # Create additional session - should work but not use pool
        extra_session = await lsp_types.Session.create(
            lsp_backend,
            base_path=base_path,
            initial_code="extra = 'not_pooled'",
            pool=session_pool,
        )

        # Should work fine
        hover_info = await extra_session.get_hover_info(
            lsp_types.Position(line=0, character=0)
        )
        assert hover_info is not None

        # Clean up
        await extra_session.shutdown()  # Not recycled
        for session in active_sessions:
            await session.shutdown()

    async def test_idle_process_cleanup(self, lsp_backend, tmp_path: Path):
        """Test that idle processes are automatically removed from the pool"""
        # Create pool with very short idle time and cleanup interval for fast test
        pool = LSPProcessPool(
            max_size=3,
            max_idle_time=0.1,  # 100ms idle time
            cleanup_interval=0.05,  # Check every 50ms
        )

        try:
            # Create and recycle a session to get a process in the pool
            session = await lsp_types.Session.create(
                lsp_backend,
                base_path=tmp_path,
                initial_code="test_var = 42",
                pool=pool,
            )
            await session.shutdown()

            # Pool should have 1 available process
            assert pool.available_count == 1
            assert pool.current_size == 1

            # Wait for process to become idle and be cleaned up
            # Wait a bit longer than idle_time + cleanup_interval
            await asyncio.sleep(0.2)

            # Force a cleanup check by calling the method directly
            await pool._remove_idle_processes()

            # Pool should be empty now (process was idle too long)
            assert pool.available_count == 0
            assert pool.current_size == 0

        finally:
            await pool.cleanup()

    async def test_idle_cleanup_preserves_active_processes(
        self, lsp_backend, tmp_path: Path
    ):
        """Test that idle cleanup only removes available processes, not active ones"""
        pool = LSPProcessPool(
            max_size=3,
            max_idle_time=0.1,  # 100ms idle time
            cleanup_interval=0.05,  # Check every 50ms
        )

        try:
            # Create and recycle one session to get it in the available pool
            session1 = await lsp_types.Session.create(
                lsp_backend,
                base_path=tmp_path,
                initial_code="var1 = 1",
                pool=pool,
            )
            await session1.shutdown()

            # Now create another session that will reuse the available process
            session2 = await lsp_types.Session.create(
                lsp_backend,
                base_path=tmp_path,
                initial_code="var2 = 2",
                pool=pool,
            )
            # Don't recycle session2, keep it active

            # Pool should have 0 available, 1 active (1 total) since the process was reused
            assert pool.available_count == 0
            assert pool.current_size == 1

            # Wait for idle cleanup
            await asyncio.sleep(0.2)
            await pool._remove_idle_processes()

            # No idle processes to remove, active process should still be there
            assert pool.available_count == 0
            assert pool.current_size == 1  # Active session still there

            # Clean up the active session
            await session2.shutdown()

            # Now there should be one available process
            assert pool.available_count == 1
            assert pool.current_size == 1

            # Wait and cleanup idle processes
            await asyncio.sleep(0.2)
            await pool._remove_idle_processes()

            # Now the idle process should be cleaned up
            assert pool.available_count == 0
            assert pool.current_size == 0

        finally:
            await pool.cleanup()

    async def test_idle_cleanup_timing_precision(self, lsp_backend, tmp_path: Path):
        """Test that idle cleanup respects the max_idle_time precisely"""
        pool = LSPProcessPool(
            max_size=2,
            max_idle_time=0.15,  # 150ms idle time
            cleanup_interval=0.05,  # Check every 50ms
        )

        try:
            # Create and recycle a session
            session = await lsp_types.Session.create(
                lsp_backend,
                base_path=tmp_path,
                initial_code="test_var = 42",
                pool=pool,
            )
            await session.shutdown()

            assert pool.available_count == 1

            # Wait less than idle time - process should still be there
            await asyncio.sleep(0.1)  # 100ms < 150ms
            await pool._remove_idle_processes()

            assert pool.available_count == 1  # Still there

            # Wait more than idle time - process should be removed
            await asyncio.sleep(0.1)  # Total 200ms > 150ms
            await pool._remove_idle_processes()

            assert pool.available_count == 0  # Should be removed now

        finally:
            await pool.cleanup()


class TestLSPProcessPoolBenchmarks:
    """Benchmark tests comparing pooled vs non-pooled session performance"""

    async def test_benchmark_session_creation_comparison(
        self, lsp_backend, backend_name, tmp_path: Path
    ):
        """Compare session creation times with and without pooling"""
        pool = LSPProcessPool(max_size=3)

        try:
            # Benchmark session creation with pooling
            pooled_times = []
            for i in range(3):
                start_time = time.perf_counter()
                session = await lsp_types.Session.create(
                    lsp_backend,
                    base_path=tmp_path,
                    initial_code=f"pooled_var_{i} = {i}",
                    pool=pool,
                )
                await session.shutdown()
                end_time = time.perf_counter()
                pooled_times.append(end_time - start_time)

            # Benchmark session creation without pooling
            non_pooled_times = []
            for i in range(3):
                start_time = time.perf_counter()
                session = await lsp_types.Session.create(
                    lsp_backend,
                    base_path=tmp_path,
                    initial_code=f"non_pooled_var_{i} = {i}",
                )
                await session.shutdown()
                end_time = time.perf_counter()
                non_pooled_times.append(end_time - start_time)

            # Calculate averages
            avg_pooled = sum(pooled_times) / len(pooled_times)
            avg_non_pooled = sum(non_pooled_times) / len(non_pooled_times)

            logging.info(f"\n{backend_name.title()} Benchmark Results:")
            logging.info(
                f"Average session creation time with pooling: {avg_pooled:.3f}s"
            )
            logging.info(
                f"Average session creation time without pooling: {avg_non_pooled:.3f}s"
            )
            logging.info(
                f"Performance improvement: {((avg_non_pooled - avg_pooled) / avg_non_pooled * 100):.1f}%"
            )

            # The second and third pooled sessions should be faster (reusing processes)
            if len(pooled_times) >= 2:
                logging.info(
                    f"First pooled session (new process): {pooled_times[0]:.3f}s"
                )
                logging.info(
                    f"Second pooled session (reused process): {pooled_times[1]:.3f}s"
                )
                logging.info(
                    f"Third pooled session (reused process): {pooled_times[2]:.3f}s"
                )

        finally:
            await pool.cleanup()

    async def test_benchmark_session_reuse_performance(
        self, lsp_backend, backend_name, tmp_path: Path
    ):
        """Compare session reuse performance vs fresh creation"""
        pool = LSPProcessPool(max_size=3)

        try:
            # Pre-warm the pool
            warmup_session = await lsp_types.Session.create(
                lsp_backend,
                base_path=tmp_path,
                initial_code="warmup = True",
                pool=pool,
            )
            await warmup_session.shutdown()

            # Benchmark session reuse (should be fast after first)
            reuse_times = []
            for i in range(5):
                start_time = time.perf_counter()
                session = await lsp_types.Session.create(
                    lsp_backend,
                    base_path=tmp_path,
                    initial_code=f"reused_var_{i} = {i}",
                    pool=pool,
                )
                # Do some work
                hover_info = await session.get_hover_info(
                    lsp_types.Position(line=0, character=0)
                )
                assert hover_info is not None
                await session.shutdown()
                end_time = time.perf_counter()
                reuse_times.append(end_time - start_time)

            # Benchmark fresh session creation for comparison
            fresh_times = []
            for i in range(3):
                start_time = time.perf_counter()
                session = await lsp_types.Session.create(
                    lsp_backend,
                    base_path=tmp_path,
                    initial_code=f"fresh_var_{i} = {i}",
                )
                hover_info = await session.get_hover_info(
                    lsp_types.Position(line=0, character=0)
                )
                assert hover_info is not None
                await session.shutdown()
                end_time = time.perf_counter()
                fresh_times.append(end_time - start_time)

            avg_reuse = sum(reuse_times) / len(reuse_times)
            avg_fresh = sum(fresh_times) / len(fresh_times)

            logging.info(f"\n{backend_name.title()} Session Reuse Benchmark:")
            logging.info(f"Average reused session time: {avg_reuse:.3f}s")
            logging.info(f"Average fresh session time: {avg_fresh:.3f}s")
            logging.info(
                f"Reuse performance improvement: {((avg_fresh - avg_reuse) / avg_fresh * 100):.1f}%"
            )

        finally:
            await pool.cleanup()

    async def test_benchmark_concurrent_session_creation(
        self, lsp_backend, backend_name, tmp_path: Path
    ):
        """Compare concurrent session creation with and without pooling"""
        pool = LSPProcessPool(max_size=5)

        try:
            # Benchmark concurrent sessions with pooling
            start_time = time.perf_counter()

            async def create_pooled_session(session_id: int):
                session = await lsp_types.Session.create(
                    lsp_backend,
                    base_path=tmp_path,
                    initial_code=f"pooled_concurrent_{session_id} = {session_id}",
                    pool=pool,
                )
                hover_info = await session.get_hover_info(
                    lsp_types.Position(line=0, character=0)
                )
                await session.shutdown()
                return hover_info is not None

            tasks = [create_pooled_session(i) for i in range(3)]
            pooled_results = await asyncio.gather(*tasks)
            pooled_time = time.perf_counter() - start_time

            # Benchmark concurrent sessions without pooling
            start_time = time.perf_counter()

            async def create_fresh_session(session_id: int):
                session = await lsp_types.Session.create(
                    lsp_backend,
                    base_path=tmp_path,
                    initial_code=f"fresh_concurrent_{session_id} = {session_id}",
                )
                hover_info = await session.get_hover_info(
                    lsp_types.Position(line=0, character=0)
                )
                await session.shutdown()
                return hover_info is not None

            tasks = [create_fresh_session(i) for i in range(3)]
            fresh_results = await asyncio.gather(*tasks)
            fresh_time = time.perf_counter() - start_time

            logging.info(
                f"\n{backend_name.title()} Concurrent Session Creation Benchmark:"
            )
            logging.info(f"3 pooled sessions time: {pooled_time:.3f}s")
            logging.info(f"3 fresh sessions time: {fresh_time:.3f}s")
            logging.info(
                f"Pooling improvement: {((fresh_time - pooled_time) / fresh_time * 100):.1f}%"
            )

            assert all(pooled_results)
            assert all(fresh_results)

        finally:
            await pool.cleanup()


# Pyrefly-specific configuration benchmark test
async def test_pyrefly_config_options_benchmark(tmp_path: Path):
    """Benchmark different Pyrefly configuration options"""
    # Only run for Pyrefly backend
    backend = PyreflyBackend()
    from lsp_types.pyrefly.config_schema import Model as PyreflyConfig

    # Test different threading configurations
    configs: list[PyreflyConfig] = [
        {"threads": 0, "verbose": False},  # Auto
        {"threads": 1, "verbose": False},  # Sequential
        {"threads": 2, "verbose": False},  # Parallel
        {"threads": 4, "verbose": False},  # More parallel
    ]

    pool = LSPProcessPool(max_size=2)

    try:
        for config in configs:
            config_times = []

            for i in range(3):
                start_time = time.perf_counter()

                session = await lsp_types.Session.create(
                    backend,
                    base_path=tmp_path,
                    initial_code=f"def test_{i}(x: int) -> int: return x * 2\nresult = test_{i}(5)",
                    options=config,  # type: ignore
                    pool=pool,
                )

                # Do some work to test performance
                hover_info = await session.get_hover_info(
                    lsp_types.Position(line=0, character=4)
                )
                assert hover_info is not None

                _diagnostics = await session.get_diagnostics()
                await session.shutdown()

                end_time = time.perf_counter()
                config_times.append(end_time - start_time)

            avg_time = sum(config_times) / len(config_times)
            logging.info(f"\nPyrefly Config {config}: Average time {avg_time:.3f}s")

    finally:
        await pool.cleanup()
