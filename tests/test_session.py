import time
import typing as t
from pathlib import Path

import pytest

import lsp_types
from lsp_types.pool import LSPProcessPool
from lsp_types.pyrefly.backend import PyreflyBackend
from lsp_types.pyrefly.config_schema import Model as PyreflyConfig
from lsp_types.pyright.backend import PyrightBackend
from lsp_types.ty.backend import TyBackend
from lsp_types.ty.config_schema import Model as TyConfig


@pytest.fixture(params=[PyrightBackend, PyreflyBackend, TyBackend])
def lsp_backend(request):
    """Parametrized fixture providing Pyright, Pyrefly, and ty backends"""
    return request.param()


@pytest.fixture
def backend_name(lsp_backend):
    """Helper fixture to get the backend name for test identification"""
    return lsp_backend.__class__.__name__.replace("Backend", "").lower()


def test_requires_file_on_disk_protocol():
    """Test that requires_file_on_disk returns correct values for each backend"""
    # Pyright and Pyrefly support virtual documents
    assert PyrightBackend().requires_file_on_disk() is False
    assert PyreflyBackend().requires_file_on_disk() is False

    # ty requires files to exist on disk
    assert TyBackend().requires_file_on_disk() is True


async def test_ty_file_written_to_disk(tmp_path: Path):
    """Test that ty backend automatically writes file to disk"""
    backend = TyBackend()
    code = "x: int = 42"

    file_path = tmp_path / "new.py"
    assert not file_path.exists(), "File should not exist before session creation"

    session = await lsp_types.Session.create(
        backend, base_path=tmp_path, initial_code=code
    )

    # File should now exist on disk
    assert file_path.exists(), "File should be written to disk for ty backend"
    assert file_path.read_text() == code

    # Update code and verify file is updated
    new_code = "y: str = 'hello'"
    await session.update_code(new_code)
    assert file_path.read_text() == new_code, "File should be updated on code change"

    await session.shutdown()


async def test_pyright_no_file_written(tmp_path: Path):
    """Test that pyright backend does NOT write file to disk (virtual docs work)"""
    backend = PyrightBackend()
    code = "x: int = 42"

    file_path = tmp_path / "new.py"
    assert not file_path.exists()

    session = await lsp_types.Session.create(
        backend, base_path=tmp_path, initial_code=code
    )

    # File should NOT exist - Pyright uses virtual documents
    assert not file_path.exists(), "Pyright should not write file to disk"

    await session.shutdown()


async def test_session_with_dynamic_environment(lsp_backend, tmp_path: Path):
    """Test LSP session with a dynamic temporary environment"""

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

    # Create a session with the temporary directory as the base_path
    session = await lsp_types.Session.create(
        lsp_backend,
        base_path=tmp_path,
        initial_code=code,
    )

    # Get diagnostics to check for any errors
    diagnostics = await session.get_diagnostics()

    # Verify no errors are reported
    assert len(diagnostics) == 0, f"Expected no diagnostics, but got: {diagnostics}"

    # Shutdown the session
    await session.shutdown()


async def test_session_diagnostics(lsp_backend, backend_name, tmp_path: Path):
    """Test diagnostic reporting for type errors"""

    code = """\
def greet(name: str) -> str:
    return name + 123
"""

    session = await lsp_types.Session.create(
        lsp_backend, base_path=tmp_path, initial_code=code
    )

    diagnostics = await session.get_diagnostics()
    assert len(diagnostics) > 0, "Expected type error diagnostic"

    # Calling get_diagnostics again should give the same result
    diagnostics = await session.get_diagnostics()
    assert len(diagnostics) > 0, "Expected type error diagnostic"

    # Verify the type error diagnostic
    error = diagnostics[0]
    assert error.get("severity", 0) == 1  # Error severity
    message = error.get("message", "")
    assert "str" in message, "Expected type error message about str return type"

    code = """\
def greet(name: str) -> str:
    return f"Hello, {name}"

print(greet("world"))
"""

    assert await session.update_code(code) == 2

    diagnostics = await session.get_diagnostics()
    assert len(diagnostics) == 0, "Expected no diagnostics after fixing type error"

    await session.shutdown()


async def test_session_hover(lsp_backend, backend_name, tmp_path: Path):
    """Test hover information for symbols"""
    code = """\
def greet(name: str) -> str:
    return f"Hello, {name}"

result = greet("world")
"""
    session = await lsp_types.Session.create(
        lsp_backend, base_path=tmp_path, initial_code=code
    )

    # Hover over the function name
    hover_info = await session.get_hover_info(lsp_types.Position(line=0, character=4))
    assert hover_info is not None

    contents = hover_info.get("contents")
    assert isinstance(contents, dict)  # MarkupContent
    assert contents.get("kind") == lsp_types.MarkupKind.Markdown
    hover_text = contents.get("value", "")
    assert "greet" in hover_text
    assert "str" in hover_text

    # Hover over the variable
    hover_info = await session.get_hover_info(lsp_types.Position(line=3, character=0))
    assert hover_info is not None

    contents = hover_info.get("contents")
    assert isinstance(contents, dict)  # MarkupContent
    assert contents.get("kind") == lsp_types.MarkupKind.Markdown
    hover_text = contents.get("value", "")
    # ty shows just the type, not "variable: type" format
    if backend_name != "ty":
        assert "result" in hover_text
    assert "str" in hover_text

    await session.shutdown()


async def test_session_rename(lsp_backend, backend_name, tmp_path: Path):
    """Test symbol renaming functionality"""

    # FIXME: Pyrefly detects file as external and disables rename edits
    if backend_name == "pyrefly":
        pytest.xfail("Pyrefly detects file as external and disables rename edits")

    code = """\
def greet(name: str) -> str:
    return f"Hello, {name}"

result = greet("world")
print(result)
"""
    session = await lsp_types.Session.create(
        lsp_backend, base_path=tmp_path, initial_code=code
    )

    # Rename the function
    rename_edits = await session.get_rename_edits(
        lsp_types.Position(line=0, character=4), "say_hello"
    )
    assert rename_edits is not None

    # Handle backend-specific response formats
    if backend_name in ("pyrefly", "ty"):
        # Pyrefly and ty use "changes" format
        assert "changes" in rename_edits
        changes = next(iter(rename_edits["changes"].values()))

        assert any(change["newText"] == "say_hello" for change in changes), (
            "Expected to find 'say_hello' in changes"
        )
    else:
        # Pyright uses "documentChanges" format
        assert "documentChanges" in rename_edits
        changes = rename_edits["documentChanges"]

        assert any(
            edit["newText"] == "say_hello"
            for change in changes
            if "edits" in change
            for edit in change["edits"]
            if "newText" in edit
        ), "Expected to find 'say_hello' in changes"

    # Rename the variable
    rename_edits = await session.get_rename_edits(
        lsp_types.Position(line=3, character=0), "greeting"
    )
    assert rename_edits is not None

    # Handle backend-specific response formats
    if backend_name in ("pyrefly", "ty"):
        # Pyrefly and ty use "changes" format
        assert "changes" in rename_edits
        changes = next(iter(rename_edits["changes"].values()))

        assert any(change["newText"] == "greeting" for change in changes), (
            "Expected to find 'greeting' in changes"
        )
    else:
        # Pyright uses "documentChanges" format
        assert "documentChanges" in rename_edits
        changes = rename_edits["documentChanges"]

        assert any(
            edit["newText"] == "greeting"
            for change in changes
            if "edits" in change
            for edit in change["edits"]
            if "newText" in edit
        ), "Expected to find 'greeting' in changes"

    await session.shutdown()


async def test_session_signature_help(lsp_backend, tmp_path: Path):
    """Test function signature help"""

    code = """\
def complex_function(a: int, b: str, c: float = 1.0) -> None:
    pass

complex_function(
"""
    session = await lsp_types.Session.create(
        lsp_backend, base_path=tmp_path, initial_code=code
    )

    # Get signature help inside the function call
    sig_help = await session.get_signature_help(
        lsp_types.Position(line=3, character=17)
    )
    assert sig_help is not None
    signatures = sig_help.get("signatures", [])
    assert len(signatures) > 0

    first_sig = signatures[0]
    sig_label = first_sig.get("label", "")
    assert "a: int" in sig_label
    assert "b: str" in sig_label

    await session.shutdown()


async def test_session_completion(lsp_backend, backend_name, tmp_path: Path):
    """Test code completion and completion item resolution"""

    code = """\
class MyClass:
    def my_method(self) -> None:
        pass

obj = MyClass()
obj.
"""
    session = await lsp_types.Session.create(
        lsp_backend, base_path=tmp_path, initial_code=code
    )

    # Get completions after the dot
    completions = await session.get_completion(lsp_types.Position(line=5, character=4))
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
    # Pyrefly and ty don't support completion resolution
    if backend_name not in ("pyrefly", "ty"):
        method_completion = method_items[0]
        resolved = await session.resolve_completion(method_completion)
        assert resolved is not None
        assert resolved.get("label") == "my_method"

    await session.shutdown()


async def test_session_semantic_tokens(lsp_backend, tmp_path: Path):
    """Test semantic token retrieval"""
    code = """\
def greet(name: str) -> str:
    return f"Hello, {name}"

result = greet("world")
"""
    session = await lsp_types.Session.create(
        lsp_backend, base_path=tmp_path, initial_code=code
    )

    # Get semantic tokens
    tokens = await session.get_semantic_tokens()
    assert tokens is not None
    token_data = tokens.get("data", [])
    # Verify we have the expected number of tokens
    # Each line should generate multiple tokens for syntax highlighting
    assert len(token_data) >= 8, "Expected at least 8 semantic tokens"

    await session.shutdown()


async def test_session_semantic_tokens_normalized(lsp_backend, tmp_path: Path):
    """Test normalized semantic token retrieval with canonical legend"""
    code = """\
def greet(name: str) -> str:
    return f"Hello, {name}"

result = greet("world")
"""
    session = await lsp_types.Session.create(
        lsp_backend, base_path=tmp_path, initial_code=code
    )

    # Check that canonical_legend is available
    canonical_legend = session.canonical_legend
    assert canonical_legend is not None
    assert "tokenTypes" in canonical_legend
    assert "tokenModifiers" in canonical_legend

    # Check that backend_legend is captured (Pyrefly uses hardcoded, others use server)
    backend_legend = session.backend_legend
    assert backend_legend is not None

    # Get raw tokens
    raw_tokens = await session.get_semantic_tokens()
    assert raw_tokens is not None
    raw_data = raw_tokens.get("data", [])
    assert len(raw_data) >= 8

    # Get normalized tokens
    normalized_tokens = await session.get_semantic_tokens(normalize=True)
    assert normalized_tokens is not None
    normalized_data = normalized_tokens.get("data", [])

    # Token count should be the same
    assert len(normalized_data) == len(raw_data)

    # Verify that tokens have different indices (due to remapping)
    # but same positions (deltaLine, deltaStart, length stay the same)
    for i in range(0, min(len(raw_data), 10), 5):  # Check first 2 tokens
        # Position values should be identical
        assert normalized_data[i] == raw_data[i]  # deltaLine
        assert normalized_data[i + 1] == raw_data[i + 1]  # deltaStart
        assert normalized_data[i + 2] == raw_data[i + 2]  # length
        # Token type and modifiers may differ due to remapping
        # (they could be same if backend uses same indices as canonical)

    await session.shutdown()


async def test_session_semantic_tokens_canonical_legend_consistency(
    lsp_backend, tmp_path: Path
):
    """Test that canonical legend is consistent across backends"""
    session = await lsp_types.Session.create(
        lsp_backend, base_path=tmp_path, initial_code="x = 1"
    )

    # The canonical legend should be the same regardless of backend
    canonical = session.canonical_legend
    assert canonical["tokenTypes"][0] == "namespace"
    assert canonical["tokenTypes"][2] == "class"
    assert canonical["tokenTypes"][8] == "variable"
    assert canonical["tokenTypes"][12] == "function"
    assert canonical["tokenTypes"][22] == "decorator"

    assert canonical["tokenModifiers"][0] == "declaration"
    assert canonical["tokenModifiers"][1] == "definition"
    assert canonical["tokenModifiers"][6] == "async"

    await session.shutdown()


async def test_session_recycling_basic(lsp_backend, tmp_path: Path):
    """Test basic session recycling functionality"""
    pool = LSPProcessPool(max_size=2)

    try:
        # Create first session with pool
        session1 = await lsp_types.Session.create(
            lsp_backend,
            base_path=tmp_path,
            initial_code="def func1(): return 1",
            pool=pool,
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
        session2 = await lsp_types.Session.create(
            lsp_backend,
            base_path=tmp_path,
            initial_code="def func2(): return 2",
            pool=pool,
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


async def test_session_recycling_with_diagnostics(
    lsp_backend, backend_name, tmp_path: Path
):
    """Test that recycling properly clears old state"""

    pool = LSPProcessPool(max_size=1)

    try:
        # First session with error
        session1 = await lsp_types.Session.create(
            lsp_backend,
            base_path=tmp_path,
            initial_code="undefined_variable",
            pool=pool,
        )

        diagnostics = await session1.get_diagnostics()
        assert len(diagnostics) > 0  # Should have error

        await session1.shutdown()

        # Second session with valid code
        session2 = await lsp_types.Session.create(
            lsp_backend, base_path=tmp_path, initial_code="x = 42", pool=pool
        )

        diagnostics = await session2.get_diagnostics()
        assert len(diagnostics) == 0  # Should be clean

        await session2.shutdown()
    finally:
        await pool.cleanup()


async def test_session_recycling_performance(lsp_backend, tmp_path: Path):
    """Test that recycling is faster than creating new sessions"""
    pool = LSPProcessPool(max_size=2)

    try:
        # Time creating fresh sessions
        start_time = time.time()
        for i in range(3):
            session = await lsp_types.Session.create(
                lsp_backend, base_path=tmp_path, initial_code=f"x{i} = {i}"
            )
            await session.shutdown()
        fresh_time = time.time() - start_time

        # Time using recycled sessions
        start_time = time.time()
        sessions = []
        for i in range(3):
            session = await lsp_types.Session.create(
                lsp_backend, base_path=tmp_path, initial_code=f"y{i} = {i}", pool=pool
            )
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


# Pyrefly-specific configuration tests
async def test_pyrefly_session_with_config_options(tmp_path: Path):
    """Test Pyrefly session creation with various configuration options"""
    # Only run for Pyrefly backend
    backend = PyreflyBackend()

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

    session = await lsp_types.Session.create(
        backend, base_path=tmp_path, initial_code=code, options=options
    )

    # Verify session works with options
    hover_info = await session.get_hover_info(lsp_types.Position(line=0, character=4))
    assert hover_info is not None
    assert "test_function" in str(hover_info)

    # Check diagnostics
    diagnostics = await session.get_diagnostics()
    assert len(diagnostics) == 0, "Expected no diagnostics for valid code"

    await session.shutdown()


async def test_pyrefly_session_with_minimal_config(tmp_path: Path):
    """Test Pyrefly session with minimal configuration"""
    # Only run for Pyrefly backend
    backend = PyreflyBackend()
    from lsp_types.pyrefly.config_schema import Model as PyreflyConfig

    # Test with minimal options
    options: PyreflyConfig = {
        "verbose": False,
        "threads": 0,  # Auto-detect
    }

    code = "x = 42"

    session = await lsp_types.Session.create(
        backend, base_path=tmp_path, initial_code=code, options=options
    )

    # Basic functionality test
    diagnostics = await session.get_diagnostics()
    assert len(diagnostics) == 0, "Expected no diagnostics for simple valid code"

    await session.shutdown()


async def test_pyrefly_arbitrary_config_fields(tmp_path):
    """Test Pyrefly backend supports arbitrary configuration fields"""
    backend = PyreflyBackend()

    # Config with both known and arbitrary fields
    config: PyreflyConfig = {
        "verbose": True,
        "threads": 4,
    }

    config |= t.cast(
        PyreflyConfig,
        {
            "custom_field": "test_value",  # Arbitrary field
            "experimental_flag": True,  # Arbitrary field
            "nested_config": {  # Arbitrary nested field
                "mode": "test",
                "value": 42,
            },
        },
    )

    # Write config file
    backend.write_config(tmp_path, config)

    # Verify TOML file was created and contains all fields
    config_path = tmp_path / "pyrefly.toml"
    assert config_path.exists(), "Config file should be created"

    # Parse TOML to verify correctness
    import tomllib

    parsed = tomllib.loads(config_path.read_text())

    # Verify known fields
    assert parsed["verbose"] is True
    assert parsed["threads"] == 4

    # Verify arbitrary fields were serialized (now in kebab-case)
    assert parsed["custom-field"] == "test_value"
    assert parsed["experimental-flag"] is True

    # Verify nested config (keys converted to kebab-case)
    assert parsed["nested-config"]["mode"] == "test"
    assert parsed["nested-config"]["value"] == 42


async def test_pyrefly_comprehensive_config_options(tmp_path):
    """Test Pyrefly session with comprehensive configuration options"""
    backend = PyreflyBackend()
    from lsp_types.pyrefly.config_schema import Model as PyreflyConfig

    # Test comprehensive config covering all major categories
    options: PyreflyConfig = {
        # Core options
        "verbose": True,
        "threads": 4,
        "color": "always",
        # LSP options
        "indexing_mode": "lazy-blocking",
        "disable_type_errors_in_ide": False,
        # File selection
        "project_includes": ["**/*.py", "**/*.pyi"],
        "project_excludes": ["**/tests/**", "**/venv/**"],
        "use_ignore_files": True,
        # Python environment (USER REQUESTED)
        "search_path": ["./src", "./lib"],
        "python_version": "3.12.0",
        "python_platform": "linux",
        "site_package_path": ["./site-packages"],
        "disable_search_path_heuristics": False,
        # Type checking behavior
        "untyped_def_behavior": "check-and-infer-return-type",
        "infer_with_first_use": True,
        "ignore_errors_in_generated_code": True,
        "permissive_ignores": False,
        "enabled_ignores": ["type", "pyrefly"],
        # Import handling
        "ignore_missing_imports": ["external_*", "legacy_*"],
        "replace_imports_with_any": ["deprecated_module"],
        "ignore_missing_source": False,
        # Error configuration
        "errors": {
            "bad-assignment": False,
            "bad-return": True,
            "undefined-variable": True,
        },
        # Advanced
        "typeshed_path": "/custom/typeshed",
    }

    # Write config and verify TOML serialization
    backend.write_config(tmp_path, options)
    config_path = tmp_path / "pyrefly.toml"
    assert config_path.exists(), "Config file should be created"

    # Parse and verify fields
    import tomllib

    parsed = tomllib.loads(config_path.read_text())

    # Verify user-requested fields (now in kebab-case)
    assert parsed["search-path"] == ["./src", "./lib"]
    assert parsed["python-version"] == "3.12.0"
    assert parsed["python-platform"] == "linux"

    # Verify file selection (now in kebab-case)
    assert parsed["project-includes"] == ["**/*.py", "**/*.pyi"]
    assert parsed["project-excludes"] == ["**/tests/**", "**/venv/**"]

    # Verify type checking (now in kebab-case)
    assert parsed["untyped-def-behavior"] == "check-and-infer-return-type"
    assert parsed["infer-with-first-use"] is True

    # Verify error config (unchanged - dict keys not affected)
    assert parsed["errors"]["bad-assignment"] is False
    assert parsed["errors"]["bad-return"] is True

    # Verify import handling (now in kebab-case)
    assert parsed["ignore-missing-imports"] == ["external_*", "legacy_*"]
    assert parsed["replace-imports-with-any"] == ["deprecated_module"]


async def test_pyrefly_search_path_configuration():
    """Test that search_path configuration enables custom import resolution"""
    backend = PyreflyBackend()
    import tempfile

    from lsp_types.pyrefly.config_schema import Model as PyreflyConfig

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create custom module directory outside base path
        lib_path = tmp_path / "custom_lib"
        lib_path.mkdir()
        (lib_path / "__init__.py").touch()

        # Create custom module
        custom_module = lib_path / "my_utils.py"
        custom_module.write_text("""
def helper_function(x: int) -> str:
    '''Convert int to string.'''
    return str(x)
""")

        # Code that imports from custom location
        code = """
from my_utils import helper_function

result = helper_function(42)
print(result)
"""

        # Configure with search_path pointing to lib directory
        options: PyreflyConfig = {
            "search_path": [str(lib_path)],
            "verbose": False,
        }

        session = await lsp_types.Session.create(
            backend,
            base_path=tmp_path,
            initial_code=code,
            options=options,
        )

        # Verify no import errors
        diagnostics = await session.get_diagnostics()
        import_errors = [
            d
            for d in diagnostics
            if "import" in d.get("message", "").lower()
            or "module" in d.get("message", "").lower()
        ]

        # Should succeed because search_path includes lib/
        assert len(import_errors) == 0, (
            f"Expected no import errors with search_path configured, got: {import_errors}"
        )

        await session.shutdown()


# ty-specific configuration tests
async def test_ty_session_with_config_options(tmp_path: Path):
    """Test ty session creation with various configuration options"""
    backend = TyBackend()

    options: TyConfig = {
        "environment": {
            "python_version": "3.12",
        },
        "rules": {
            "possibly-unresolved-reference": "warn",
        },
    }

    code = """\
def test_function(x: int) -> int:
    return x * 2

result = test_function(5)
"""
    # ty requires files to exist on disk for diagnostics
    (tmp_path / "new.py").write_text(code)

    session = await lsp_types.Session.create(
        backend, base_path=tmp_path, initial_code=code, options=options
    )

    hover_info = await session.get_hover_info(lsp_types.Position(line=0, character=4))
    assert hover_info is not None
    assert "test_function" in str(hover_info)

    diagnostics = await session.get_diagnostics()
    assert len(diagnostics) == 0, "Expected no diagnostics for valid code"

    await session.shutdown()


async def test_ty_nested_config_serialization(tmp_path: Path):
    """Test ty backend correctly serializes nested config sections"""
    backend = TyBackend()

    config: TyConfig = {
        "environment": {
            "python_version": "3.12",
            "extra_paths": ["./lib", "./src"],
            "python_platform": "linux",
        },
        "src": {
            "include": ["**/*.py"],
            "exclude": ["**/tests/**"],
            "respect_ignore_files": True,
        },
        "rules": {
            "unused-ignore-comment": "warn",
            "possibly-unresolved-reference": "error",
        },
        "terminal": {
            "output_format": "full",
            "error_on_warning": False,
        },
    }

    backend.write_config(tmp_path, config)

    # Verify TOML file
    import tomllib

    config_path = tmp_path / "ty.toml"
    assert config_path.exists()

    parsed = tomllib.loads(config_path.read_text())

    # Verify nested sections with kebab-case keys
    assert parsed["environment"]["python-version"] == "3.12"
    assert parsed["environment"]["extra-paths"] == ["./lib", "./src"]
    assert parsed["src"]["respect-ignore-files"] is True
    assert parsed["rules"]["unused-ignore-comment"] == "warn"
    assert parsed["terminal"]["output-format"] == "full"


async def test_ty_extra_paths_configuration(tmp_path: Path):
    """Test that extra_paths configuration enables custom import resolution"""
    backend = TyBackend()

    # Create custom module directory outside base path
    lib_path = tmp_path / "custom_lib"
    lib_path.mkdir()
    (lib_path / "__init__.py").touch()

    # Create custom module
    custom_module = lib_path / "my_utils.py"
    custom_module.write_text("""
def helper_function(x: int) -> str:
    '''Convert int to string.'''
    return str(x)
""")

    # Code that imports from custom location
    code = """
from my_utils import helper_function

result = helper_function(42)
print(result)
"""
    # ty requires files to exist on disk for diagnostics
    (tmp_path / "new.py").write_text(code)

    # Configure with extra_paths pointing to lib directory
    options: TyConfig = {
        "environment": {
            "extra_paths": [str(lib_path)],
        },
    }

    session = await lsp_types.Session.create(
        backend,
        base_path=tmp_path,
        initial_code=code,
        options=options,
    )

    # Verify no import errors
    diagnostics = await session.get_diagnostics()
    import_errors = [
        d
        for d in diagnostics
        if "import" in d.get("message", "").lower()
        or "module" in d.get("message", "").lower()
    ]

    # Should succeed because extra_paths includes lib/
    assert len(import_errors) == 0, (
        f"Expected no import errors with extra_paths configured, got: {import_errors}"
    )

    await session.shutdown()
