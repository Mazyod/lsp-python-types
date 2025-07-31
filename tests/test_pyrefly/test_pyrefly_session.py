from pathlib import Path

import lsp_types
from lsp_types.pool import LSPProcessPool
from lsp_types.pyrefly.session import PyreflySession


async def test_pyrefly_session_with_dynamic_environment(tmp_path: Path):
    """Test Pyrefly session with a dynamic temporary environment"""

    module_path = tmp_path / "mymodule"
    module_path.mkdir()

    # Create a utils.py file with a simple function
    utils_file = module_path / "utils.py"
    utils_content = """\
def add_numbers(a: int, b: int) -> int:
    '''Add two numbers together.'''
    return a + b
"""
    utils_file.write_text(utils_content)
    module_path.joinpath("__init__.py").touch()

    # Create code that imports from the utils.py file
    code = """\
from mymodule.utils import add_numbers

result = add_numbers(5, 10)
print(f"The result is: {result}")
"""

    # Create a Pyrefly session with the temporary directory as the base_path
    pyrefly_session = await PyreflySession.create(
        base_path=tmp_path,
        initial_code=code,
    )

    # Get diagnostics to check for any errors
    diagnostics = await pyrefly_session.get_diagnostics()
    diags = diagnostics.get("diagnostics", [])

    # Verify no errors are reported
    assert len(diags) == 0, f"Expected no diagnostics, but got: {diags}"

    # Shutdown the Pyrefly session
    await pyrefly_session.shutdown()


async def test_pyrefly_session_diagnostics():
    """Test diagnostic reporting for type errors"""
    code = """\
def greet(name: str) -> str:
    return name + 123
"""

    pyrefly_session = await PyreflySession.create(initial_code=code)
    diagnostics = await pyrefly_session.get_diagnostics()

    diags = diagnostics.get("diagnostics", [])
    assert len(diags) > 0, "Expected type error diagnostic"

    # Verify the type error diagnostic
    error = diags[0]
    assert error.get("severity", 0) == 1  # Error severity
    message = error.get("message", "")
    assert "str" in message, "Expected type error message about str return type"

    code = """\
def greet(name: str) -> str:
    return f"Hello, {name}"

print(greet("world"))
"""

    assert await pyrefly_session.update_code(code) == 2

    diagnostics = await pyrefly_session.get_diagnostics()
    diags = diagnostics.get("diagnostics", [])
    assert len(diags) == 0, "Expected no diagnostics after fixing type error"

    await pyrefly_session.shutdown()


async def test_pyrefly_session_hover():
    """Test hover information for symbols"""
    code = """\
def greet(name: str) -> str:
    return f"Hello, {name}"

result = greet("world")
"""
    pyrefly_session = await PyreflySession.create(initial_code=code)

    # Hover over the function name
    hover_info = await pyrefly_session.get_hover_info(
        lsp_types.Position(line=0, character=4)
    )
    assert hover_info is not None

    contents = hover_info.get("contents")
    assert isinstance(contents, dict)  # MarkupContent
    assert contents.get("kind") == lsp_types.MarkupKind.Markdown
    hover_text = contents.get("value", "")
    assert "greet" in hover_text
    assert "str" in hover_text

    # Hover over the variable
    hover_info = await pyrefly_session.get_hover_info(
        lsp_types.Position(line=3, character=0)
    )
    assert hover_info is not None

    contents = hover_info.get("contents")
    assert isinstance(contents, dict)  # MarkupContent
    assert contents.get("kind") == lsp_types.MarkupKind.Markdown
    hover_text = contents.get("value", "")
    assert "result" in hover_text
    assert "str" in hover_text

    await pyrefly_session.shutdown()


async def test_pyrefly_session_rename():
    """Test symbol renaming functionality"""
    code = """\
def greet(name: str) -> str:
    return f"Hello, {name}"

result = greet("world")
print(result)
"""
    pyrefly_session = await PyreflySession.create(initial_code=code)

    # Rename the function
    rename_edits = await pyrefly_session.get_rename_edits(
        lsp_types.Position(line=0, character=4), "say_hello"
    )

    # destruct edits response
    match rename_edits:
        case {"changes": {"file:///test.py": changes}}:
            pass
        case _:
            assert False, "Failed to parse rename edits"

    # Verify the changes include the function rename
    assert any(
        change["newText"] == "say_hello"
        for change in changes
    ), "Expected to find 'say_hello' in changes"

    # Rename the variable
    rename_edits = await pyrefly_session.get_rename_edits(
        lsp_types.Position(line=3, character=0), "greeting"
    )

    # destruct edits response
    match rename_edits:
        case {"changes": {"file:///test.py": changes}}:
            pass
        case _:
            assert False, "Failed to parse rename edits"

    # Verify the changes include the variable rename
    assert any(
        change["newText"] == "greeting"
        for change in changes
    ), "Expected to find 'greeting' in changes"

    await pyrefly_session.shutdown()


async def test_pyrefly_session_signature_help():
    """Test function signature help"""

    code = """\
def complex_function(a: int, b: str, c: float = 1.0) -> None:
    pass

complex_function(
"""
    pyrefly_session = await PyreflySession.create(initial_code=code)

    # Get signature help inside the function call
    sig_help = await pyrefly_session.get_signature_help(
        lsp_types.Position(line=3, character=17)
    )
    assert sig_help is not None
    signatures = sig_help.get("signatures", [])
    assert len(signatures) > 0

    first_sig = signatures[0]
    sig_label = first_sig.get("label", "")
    assert "a: int" in sig_label
    assert "b: str" in sig_label

    await pyrefly_session.shutdown()


async def test_pyrefly_session_completion():
    """Test code completion and completion item resolution"""
    code = """\
class MyClass:
    def my_method(self) -> None:
        pass

obj = MyClass()
obj.
"""
    pyrefly_session = await PyreflySession.create(initial_code=code)

    # Get completions after the dot
    completions = await pyrefly_session.get_completion(
        lsp_types.Position(line=5, character=4)
    )
    assert completions is not None

    # Should be either a CompletionList or list of CompletionItem
    if isinstance(completions, dict):
        items = completions.get("items", [])
    else:
        items = completions

    # Find my_method in completions
    method_items = [item for item in items if item.get("label") == "my_method"]
    assert len(method_items) > 0, "my_method not found in completion items"

    # Resolve a completion item for more details
    # FIXME: not supported by pyrefly yet
    # method_completion = method_items[0]
    # resolved = await pyrefly_session.resolve_completion(method_completion)
    # assert resolved is not None
    # assert resolved.get("label") == "my_method"

    await pyrefly_session.shutdown()


async def test_pyrefly_session_semantic_tokens():
    """Test semantic token retrieval"""
    code = """\
def greet(name: str) -> str:
    return f"Hello, {name}"

result = greet("world")
"""
    pyrefly_session = await PyreflySession.create(initial_code=code)

    # Get semantic tokens
    tokens = await pyrefly_session.get_semantic_tokens()
    assert tokens is not None
    token_data = tokens.get("data", [])
    # Verify we have the expected number of tokens
    # Each line should generate multiple tokens for syntax highlighting
    assert len(token_data) >= 8, "Expected at least 8 semantic tokens"

    await pyrefly_session.shutdown()


async def test_pyrefly_session_recycling_basic():
    """Test basic session recycling functionality"""
    pool = LSPProcessPool(max_size=2)

    try:
        # Create first session with pool
        session1 = await PyreflySession.create(
            initial_code="def func1(): return 1", pool=pool
        )

        # Verify it works
        hover_info = await session1.get_hover_info(
            lsp_types.Position(line=0, character=4)
        )
        assert hover_info is not None
        assert "func1" in str(hover_info)

        # Recycle the session
        await session1.shutdown()

        # Pool should have one available session now
        assert pool.available_count == 1

        # Create second session - should reuse the recycled one
        session2 = await PyreflySession.create(
            initial_code="def func2(): return 2", pool=pool
        )

        # Verify new code is active
        hover_info = await session2.get_hover_info(
            lsp_types.Position(line=0, character=4)
        )
        assert hover_info is not None
        assert "func2" in str(hover_info)

        await session2.shutdown()
    finally:
        await pool.cleanup()


async def test_pyrefly_session_recycling_with_diagnostics():
    """Test that recycling properly clears old state"""
    pool = LSPProcessPool(max_size=1)

    try:
        # First session with error
        session1 = await PyreflySession.create(
            initial_code="undefined_variable", pool=pool
        )

        diagnostics = await session1.get_diagnostics()
        diags = diagnostics.get("diagnostics", [])
        assert len(diags) > 0  # Should have error

        await session1.shutdown()

        # Second session with valid code
        session2 = await PyreflySession.create(initial_code="x = 42", pool=pool)

        diagnostics = await session2.get_diagnostics()
        diags = diagnostics.get("diagnostics", [])
        assert len(diags) == 0  # Should be clean

        await session2.shutdown()
    finally:
        await pool.cleanup()


async def test_pyrefly_session_recycling_performance():
    """Test that recycling is faster than creating new sessions"""
    import time

    pool = LSPProcessPool(max_size=2)

    try:
        # Time creating fresh sessions
        start_time = time.time()
        for i in range(3):
            session = await PyreflySession.create(initial_code=f"x{i} = {i}")
            await session.shutdown()
        fresh_time = time.time() - start_time

        # Time using recycled sessions
        start_time = time.time()
        sessions = []
        for i in range(3):
            session = await PyreflySession.create(initial_code=f"y{i} = {i}", pool=pool)
            sessions.append(session)

        # Recycle them
        for session in sessions:
            await session.shutdown()

        recycled_time = time.time() - start_time

        # Recycling should be at least somewhat faster
        # Note: This is more of a performance indicator than a strict test
        assert recycled_time <= fresh_time * 1.5  # Allow some variance

    finally:
        await pool.cleanup()


async def test_pyrefly_session_with_config_options():
    """Test Pyrefly session creation with various configuration options"""
    from lsp_types.pyrefly.config_schema import Model as PyreflyConfig

    # Test with verbose and threading options
    options: PyreflyConfig = {
        "verbose": True,
        "threads": 2,
        "indexing_mode": "lazy-non-blocking-background",
        "color": "always",
    }

    code = """\
def test_function(x: int) -> int:
    return x * 2

result = test_function(5)
"""

    pyrefly_session = await PyreflySession.create(initial_code=code, options=options)

    # Verify session works with options
    hover_info = await pyrefly_session.get_hover_info(
        lsp_types.Position(line=0, character=4)
    )
    assert hover_info is not None
    assert "test_function" in str(hover_info)

    # Check diagnostics
    diagnostics = await pyrefly_session.get_diagnostics()
    diags = diagnostics.get("diagnostics", [])
    assert len(diags) == 0, "Expected no diagnostics for valid code"

    await pyrefly_session.shutdown()


async def test_pyrefly_session_with_minimal_config():
    """Test Pyrefly session with minimal configuration"""
    from lsp_types.pyrefly.config_schema import Model as PyreflyConfig

    # Test with minimal options
    options: PyreflyConfig = {
        "verbose": False,
        "threads": 0,  # Auto-detect
    }

    code = "x = 42"

    pyrefly_session = await PyreflySession.create(initial_code=code, options=options)

    # FIXME: if we lag a bit, we miss the diagnostics and hang indefinitely!
    # await asyncio.sleep(2)

    # Basic functionality test
    diagnostics = await pyrefly_session.get_diagnostics()
    diags = diagnostics.get("diagnostics", [])
    assert len(diags) == 0, "Expected no diagnostics for simple valid code"

    await pyrefly_session.shutdown()
