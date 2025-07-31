"""
Tests for Pyrefly session pool functionality.
"""

import asyncio
import tempfile
import time
from pathlib import Path

import pytest

import lsp_types
from lsp_types.pyrefly.config_schema import Model as PyreflyConfig
from lsp_types.pyrefly.session import PyreflySession


class TestPyreflySessionPool:
    """Test Pyrefly session pool functionality"""

    @pytest.fixture
    async def session_pool(self):
        """Create a session pool for testing"""
        from lsp_types.pool import LSPProcessPool

        pool = LSPProcessPool(max_size=3)
        yield pool
        await pool.cleanup()

    async def test_session_pool_creation(self, session_pool):
        """Test that session pool can be created with proper configuration"""
        assert session_pool.max_size == 3
        assert session_pool.current_size == 0
        assert session_pool.available_count == 0

    async def test_session_pool_acquire_and_recycle(self, session_pool):
        """Test basic session acquisition and recycling"""
        # Create a session using the pool
        session = await PyreflySession.create(initial_code="x = 1", pool=session_pool)

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

    async def test_session_recycling_with_different_code(self, session_pool):
        """Test that recycled sessions work correctly with different code"""
        # First session with initial code
        session1 = await PyreflySession.create(
            initial_code="def func1(): pass", pool=session_pool
        )

        # Check that the function exists
        hover_info = await session1.get_hover_info(
            lsp_types.Position(line=0, character=4)
        )
        assert hover_info is not None
        assert "func1" in str(hover_info)

        await session1.shutdown()

        # Second session with different code - should reuse the recycled session
        session2 = await PyreflySession.create(
            initial_code="def func2(): pass", pool=session_pool
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

    async def test_session_recycling_with_different_options(self, session_pool):
        """Test recycling sessions with different Pyrefly options"""
        options1: PyreflyConfig = {"verbose": True, "threads": 1}
        options2: PyreflyConfig = {"verbose": False, "threads": 2}

        # First session with verbose enabled
        session1 = await PyreflySession.create(
            initial_code="test_var = 1", options=options1, pool=session_pool
        )

        await session1.shutdown()

        # Second session with different options - should update configuration
        session2 = await PyreflySession.create(
            initial_code="x: int = 42",
            options=options2,
            pool=session_pool,
        )

        # Warm up the session with new code
        await session2.update_code("x: int = 42")

        await session2.shutdown()

    async def test_session_pool_max_size_limit(self, session_pool):
        """Test that pool respects max size limit"""
        sessions = []

        # Create sessions up to max size
        for i in range(session_pool.max_size):
            session = await PyreflySession.create(
                initial_code=f"x{i} = {i}", pool=session_pool
            )
            sessions.append(session)

        # All sessions should be created
        assert session_pool.current_size == 3

        # Try to create one more session - should create a new process (not pooled)
        extra_session = await PyreflySession.create(
            initial_code="extra = 999", pool=session_pool
        )
        sessions.append(extra_session)

        # Pool size should still be at max, but we have 4 active sessions
        assert session_pool.current_size == 3

        # Clean up all sessions
        for session in sessions:
            if hasattr(session, "recycle"):
                await session.shutdown()
            else:
                await session.shutdown()

    async def test_concurrent_session_usage(self, session_pool):
        """Test concurrent session acquisition and usage"""

        async def use_session(session_id: int):
            session = await PyreflySession.create(
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

    async def test_session_warmup_on_recycle(self, session_pool):
        """Test that recycled sessions are properly warmed up with new code"""
        # Create session with initial code
        session1 = await PyreflySession.create(
            initial_code="old_var = 'old_value'", pool=session_pool
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
        session2 = await PyreflySession.create(initial_code=new_code, pool=session_pool)

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
        diags = diagnostics.get("diagnostics", [])

        # Should have error about undefined variable
        assert len(diags) > 0
        assert any("old_var" in diag.get("message", "") for diag in diags)

        await session2.shutdown()

    async def test_session_pool_cleanup(self, session_pool):
        """Test proper cleanup of session pool resources"""
        # Create and recycle a session
        session = await PyreflySession.create(
            initial_code="test_var = 42", pool=session_pool
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

    async def test_session_pool_with_temp_directory(self):
        """Test session pool works with temporary directories"""
        from lsp_types.pool import LSPProcessPool

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
                session1 = await PyreflySession.create(
                    base_path=temp_path,
                    initial_code="from mymodule.utils import helper\nresult = helper()",
                    pool=pool,
                )

                diagnostics = await session1.get_diagnostics()
                diags = diagnostics.get("diagnostics", [])
                assert len(diags) == 0  # No import errors

                await session1.shutdown()

                # Second session with same base path
                session2 = await PyreflySession.create(
                    base_path=temp_path,
                    initial_code="from mymodule.utils import helper\nprint(helper())",
                    pool=pool,
                )

                diagnostics = await session2.get_diagnostics()
                diags = diagnostics.get("diagnostics", [])
                assert len(diags) == 0  # No import errors

                await session2.shutdown()

        finally:
            await pool.cleanup()

    async def test_pool_exhaustion_fallback(self, session_pool):
        """Test that pool exhaustion gracefully falls back to new sessions"""
        # Fill up the pool
        active_sessions = []
        for i in range(session_pool.max_size):
            session = await PyreflySession.create(
                initial_code=f"x{i} = {i}", pool=session_pool
            )
            active_sessions.append(session)

        # Pool should be at capacity
        assert session_pool.current_size == session_pool.max_size
        assert session_pool.available_count == 0

        # Create additional session - should work but not use pool
        extra_session = await PyreflySession.create(
            initial_code="extra = 'not_pooled'", pool=session_pool
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

    async def test_idle_process_cleanup(self):
        """Test that idle processes are automatically removed from the pool"""
        from lsp_types.pool import LSPProcessPool

        # Create pool with very short idle time and cleanup interval for fast test
        pool = LSPProcessPool(
            max_size=3,
            max_idle_time=0.1,  # 100ms idle time
            cleanup_interval=0.05,  # Check every 50ms
        )

        try:
            # Create and recycle a session to get a process in the pool
            session = await PyreflySession.create(
                initial_code="test_var = 42", pool=pool
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

    async def test_idle_cleanup_preserves_active_processes(self):
        """Test that idle cleanup only removes available processes, not active ones"""
        from lsp_types.pool import LSPProcessPool

        pool = LSPProcessPool(
            max_size=3,
            max_idle_time=0.1,  # 100ms idle time
            cleanup_interval=0.05,  # Check every 50ms
        )

        try:
            # Create and recycle one session to get it in the available pool
            session1 = await PyreflySession.create(initial_code="var1 = 1", pool=pool)
            await session1.shutdown()

            # Now create another session that will reuse the available process
            session2 = await PyreflySession.create(initial_code="var2 = 2", pool=pool)
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

    async def test_idle_cleanup_timing_precision(self):
        """Test that idle cleanup respects the max_idle_time precisely"""
        from lsp_types.pool import LSPProcessPool

        pool = LSPProcessPool(
            max_size=2,
            max_idle_time=0.15,  # 150ms idle time
            cleanup_interval=0.05,  # Check every 50ms
        )

        try:
            # Create and recycle a session
            session = await PyreflySession.create(
                initial_code="test_var = 42", pool=pool
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


class TestPyreflySessionPoolBenchmarks:
    """Benchmark tests comparing pooled vs non-pooled Pyrefly session performance"""

    async def test_benchmark_session_creation_comparison(self):
        """Compare session creation times with and without pooling"""
        from lsp_types.pool import LSPProcessPool

        pool = LSPProcessPool(max_size=3)

        try:
            # Benchmark session creation with pooling
            pooled_times = []
            for i in range(3):
                start_time = time.perf_counter()
                session = await PyreflySession.create(
                    initial_code=f"pooled_var_{i} = {i}", pool=pool
                )
                await session.shutdown()
                end_time = time.perf_counter()
                pooled_times.append(end_time - start_time)

            # Benchmark session creation without pooling
            non_pooled_times = []
            for i in range(3):
                start_time = time.perf_counter()
                session = await PyreflySession.create(
                    initial_code=f"non_pooled_var_{i} = {i}"
                )
                await session.shutdown()
                end_time = time.perf_counter()
                non_pooled_times.append(end_time - start_time)

            # Calculate averages
            avg_pooled = sum(pooled_times) / len(pooled_times)
            avg_non_pooled = sum(non_pooled_times) / len(non_pooled_times)

            print("\nPyrefly Benchmark Results:")
            print(f"Average session creation time with pooling: {avg_pooled:.3f}s")
            print(
                f"Average session creation time without pooling: {avg_non_pooled:.3f}s"
            )
            print(
                f"Performance improvement: {((avg_non_pooled - avg_pooled) / avg_non_pooled * 100):.1f}%"
            )

            # The second and third pooled sessions should be faster (reusing processes)
            if len(pooled_times) >= 2:
                print(f"First pooled session (new process): {pooled_times[0]:.3f}s")
                print(f"Second pooled session (reused process): {pooled_times[1]:.3f}s")
                print(f"Third pooled session (reused process): {pooled_times[2]:.3f}s")

        finally:
            await pool.cleanup()

    async def test_benchmark_session_reuse_performance(self):
        """Compare session reuse performance vs fresh creation"""
        from lsp_types.pool import LSPProcessPool

        pool = LSPProcessPool(max_size=3)

        try:
            # Pre-warm the pool
            warmup_session = await PyreflySession.create(
                initial_code="warmup = True", pool=pool
            )
            await warmup_session.shutdown()

            # Benchmark session reuse (should be fast after first)
            reuse_times = []
            for i in range(5):
                start_time = time.perf_counter()
                session = await PyreflySession.create(
                    initial_code=f"reused_var_{i} = {i}", pool=pool
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
                session = await PyreflySession.create(
                    initial_code=f"fresh_var_{i} = {i}"
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

            print("\nPyrefly Session Reuse Benchmark:")
            print(f"Average reused session time: {avg_reuse:.3f}s")
            print(f"Average fresh session time: {avg_fresh:.3f}s")
            print(
                f"Reuse performance improvement: {((avg_fresh - avg_reuse) / avg_fresh * 100):.1f}%"
            )

        finally:
            await pool.cleanup()

    async def test_benchmark_concurrent_session_creation(self):
        """Compare concurrent session creation with and without pooling"""
        from lsp_types.pool import LSPProcessPool

        pool = LSPProcessPool(max_size=5)

        try:
            # Benchmark concurrent sessions with pooling
            start_time = time.perf_counter()

            async def create_pooled_session(session_id: int):
                session = await PyreflySession.create(
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
                session = await PyreflySession.create(
                    initial_code=f"fresh_concurrent_{session_id} = {session_id}"
                )
                hover_info = await session.get_hover_info(
                    lsp_types.Position(line=0, character=0)
                )
                await session.shutdown()
                return hover_info is not None

            tasks = [create_fresh_session(i) for i in range(3)]
            fresh_results = await asyncio.gather(*tasks)
            fresh_time = time.perf_counter() - start_time

            print("\nPyrefly Concurrent Session Creation Benchmark:")
            print(f"3 pooled sessions time: {pooled_time:.3f}s")
            print(f"3 fresh sessions time: {fresh_time:.3f}s")
            print(
                f"Pooling improvement: {((fresh_time - pooled_time) / fresh_time * 100):.1f}%"
            )

            assert all(pooled_results)
            assert all(fresh_results)

        finally:
            await pool.cleanup()

    async def test_pyrefly_config_options_benchmark(self):
        """Benchmark different Pyrefly configuration options"""
        from lsp_types.pool import LSPProcessPool

        # Test different threading configurations
        configs = [
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
                    
                    session = await PyreflySession.create(
                        initial_code=f"def test_{i}(x: int) -> int: return x * 2\nresult = test_{i}(5)",
                        options=config,  # type: ignore
                        pool=pool
                    )
                    
                    # Do some work to test performance
                    hover_info = await session.get_hover_info(
                        lsp_types.Position(line=0, character=4)
                    )
                    assert hover_info is not None
                    
                    diagnostics = await session.get_diagnostics()
                    await session.shutdown()
                    
                    end_time = time.perf_counter()
                    config_times.append(end_time - start_time)
                
                avg_time = sum(config_times) / len(config_times)
                print(f"\nConfig {config}: Average time {avg_time:.3f}s")

        finally:
            await pool.cleanup()