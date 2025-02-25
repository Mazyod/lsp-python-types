from pathlib import Path

import lsp_types
from lsp_types.pyright.session import PyrightSession


async def test_pyright_session_with_dynamic_environment():
    """Test Pyright session with a dynamic temporary environment"""
    import tempfile

    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        module_path = temp_path / "mymodule"
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

        # Create a Pyright session with the temporary directory as the base_path
        pyright_session = await PyrightSession.create(
            base_path=temp_path,
            initial_code=code,
            options={"include": ["."]},  # Include the current directory for imports
        )

        # Get diagnostics to check for any errors
        diagnostics = await pyright_session.get_diagnostics()
        diags = diagnostics.get("diagnostics", [])

        # Verify no errors are reported
        assert len(diags) == 0, f"Expected no diagnostics, but got: {diags}"

        # Shutdown the Pyright session
        await pyright_session.shutdown()


async def test_pyright_session_diagnostics():
    """Test diagnostic reporting for type errors"""
    code = """\
def greet(name: str) -> str:
    return name + 123
"""

    pyright_session = await PyrightSession.create(initial_code=code)
    diagnostics = await pyright_session.get_diagnostics()

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

    assert await pyright_session.update_code(code) == 2

    diagnostics = await pyright_session.get_diagnostics()
    diags = diagnostics.get("diagnostics", [])
    assert len(diags) == 0, "Expected no diagnostics after fixing type error"

    await pyright_session.shutdown()


async def test_pyright_session_hover():
    """Test hover information for symbols"""
    code = """\
def greet(name: str) -> str:
    return f"Hello, {name}"

result = greet("world")
"""
    pyright_session = await PyrightSession.create(initial_code=code)

    # Hover over the function name
    hover_info = await pyright_session.get_hover_info(
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
    hover_info = await pyright_session.get_hover_info(
        lsp_types.Position(line=3, character=0)
    )
    assert hover_info is not None

    contents = hover_info.get("contents")
    assert isinstance(contents, dict)  # MarkupContent
    assert contents.get("kind") == lsp_types.MarkupKind.Markdown
    hover_text = contents.get("value", "")
    assert "result" in hover_text
    assert "str" in hover_text

    await pyright_session.shutdown()


async def test_pyright_session_rename():
    """Test symbol renaming functionality"""
    code = """\
def greet(name: str) -> str:
    return f"Hello, {name}"

result = greet("world")
print(result)
"""
    pyright_session = await PyrightSession.create(initial_code=code)

    # Rename the function
    rename_edits = await pyright_session.get_rename_edits(
        lsp_types.Position(line=0, character=4), "say_hello"
    )
    assert rename_edits is not None
    assert "documentChanges" in rename_edits
    changes = rename_edits["documentChanges"]
    # Verify the changes include the function rename
    assert any(
        edit["newText"] == "say_hello"
        for change in changes
        if "edits" in change
        for edit in change["edits"]
        if "newText" in edit
    ), "Expected to find 'say_hello' in changes"

    # Rename the variable
    rename_edits = await pyright_session.get_rename_edits(
        lsp_types.Position(line=3, character=0), "greeting"
    )
    assert rename_edits is not None
    assert "documentChanges" in rename_edits
    changes = rename_edits["documentChanges"]
    # Verify the changes include the variable rename
    assert any(
        edit["newText"] == "greeting"
        for change in changes
        if "edits" in change
        for edit in change["edits"]
        if "newText" in edit
    ), "Expected to find 'greeting' in changes"

    await pyright_session.shutdown()


async def test_pyright_session_signature_help():
    """Test function signature help"""

    code = """\
def complex_function(a: int, b: str, c: float = 1.0) -> None:
    pass

complex_function(
"""
    pyright_session = await PyrightSession.create(initial_code=code)

    # Get signature help inside the function call
    sig_help = await pyright_session.get_signature_help(
        lsp_types.Position(line=3, character=17)
    )
    assert sig_help is not None
    signatures = sig_help.get("signatures", [])
    assert len(signatures) > 0

    first_sig = signatures[0]
    sig_label = first_sig.get("label", "")
    assert "a: int" in sig_label
    assert "b: str" in sig_label

    await pyright_session.shutdown()


async def test_pyright_session_completion():
    """Test code completion and completion item resolution"""
    code = """\
class MyClass:
    def my_method(self) -> None:
        pass

obj = MyClass()
obj.
"""
    pyright_session = await PyrightSession.create(initial_code=code)

    # Get completions after the dot
    completions = await pyright_session.get_completion(
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
    method_completion = method_items[0]
    resolved = await pyright_session.resolve_completion(method_completion)
    assert resolved is not None
    assert resolved.get("label") == "my_method"

    await pyright_session.shutdown()


async def test_pyright_session_semantic_tokens():
    """Test semantic token retrieval"""
    code = """\
def greet(name: str) -> str:
    return f"Hello, {name}"

result = greet("world")
"""
    pyright_session = await PyrightSession.create(initial_code=code)

    # Get semantic tokens
    tokens = await pyright_session.get_semantic_tokens()
    assert tokens is not None
    token_data = tokens.get("data", [])
    # Verify we have the expected number of tokens
    # Each line should generate multiple tokens for syntax highlighting
    assert len(token_data) >= 8, "Expected at least 8 semantic tokens"

    await pyright_session.shutdown()
