# Pyrefly configuration schema
# Based on official Pyrefly documentation: https://pyrefly.org/en/docs/configuration/
# CLI reference: https://github.com/facebook/pyrefly
#
# Note: Field names use snake_case (Python convention) but are automatically
# converted to kebab-case when written to pyrefly.toml (official format).

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

# Basic configuration options based on Pyrefly CLI
IndexingMode = Literal["none", "lazy-non-blocking-background", "lazy-blocking"]

# Type checking behavior options
UntypedDefBehavior = Literal[
    "check-and-infer-return-type",
    "check-and-infer-return-any",
    "skip-and-infer-return-any",
]

# Error severity configuration (error-code -> enabled/disabled)
ErrorConfig = dict[str, bool]


class Model(TypedDict):
    """
    Pyrefly Configuration Schema

    Comprehensive type definitions for all Pyrefly configuration options.
    Field names use snake_case following Python conventions. Pyrefly accepts
    both snake_case and kebab-case in TOML configuration files.

    All fields are NotRequired for maximum flexibility. For arbitrary fields
    not yet in this schema:
    - Use cast(dict, config) to add extra keys
    - Or pass plain dict to write_config (accepts Mapping[str, Any])

    Official Documentation: https://pyrefly.org/en/docs/configuration/
    """

    # ========================================================================
    # CORE OPTIONS (CLI-compatible)
    # ========================================================================

    verbose: NotRequired[bool]
    """Enable detailed logging output"""

    threads: NotRequired[int]
    """Thread count (0=auto, 1=sequential, >1=parallel)"""

    color: NotRequired[Literal["auto", "always", "never"]]
    """Control colored output in terminal"""

    # ========================================================================
    # LSP SERVER OPTIONS
    # ========================================================================

    indexing_mode: NotRequired[IndexingMode]
    """Indexing strategy for LSP server (default: lazy-non-blocking-background)"""

    disable_type_errors_in_ide: NotRequired[bool]
    """Hide type errors when running in IDE/language server mode"""

    # ========================================================================
    # FILE SELECTION
    # ========================================================================

    project_includes: NotRequired[list[str]]
    """Glob patterns for files to type check (default: ["**/*.py*"])"""

    project_excludes: NotRequired[list[str]]
    """Glob patterns to exclude from type checking"""

    disable_project_excludes_heuristics: NotRequired[bool]
    """Disable automatic exclusion patterns (allows custom specification)"""

    use_ignore_files: NotRequired[bool]
    """Use .gitignore, .ignore, .git/info/exclude for exclusions (default: true)"""

    # ========================================================================
    # PYTHON ENVIRONMENT (User-requested: search_path, python_version)
    # ========================================================================

    search_path: NotRequired[list[str]]
    """Directories where imports are resolved from (USER REQUESTED)"""

    disable_search_path_heuristics: NotRequired[bool]
    """Prevent automatic search path detection"""

    site_package_path: NotRequired[list[str]]
    """Third-party package directories for import resolution"""

    python_version: NotRequired[str]
    """Python version for sys.version checks, e.g. "3.13.0" (USER REQUESTED)"""

    python_platform: NotRequired[str]
    """Platform for sys.platform checks, e.g. "linux", "darwin", "win32" """

    conda_environment: NotRequired[str]
    """Conda environment name for querying Python configuration"""

    python_interpreter_path: NotRequired[str]
    """Path to Python executable for environment detection"""

    fallback_python_interpreter_name: NotRequired[str]
    """Interpreter name on $PATH for automatic discovery (default: "python3")"""

    skip_interpreter_query: NotRequired[bool]
    """Skip querying Python interpreter for environment setup"""

    # ========================================================================
    # TYPE CHECKING BEHAVIOR
    # ========================================================================

    typeshed_path: NotRequired[str]
    """Override bundled typeshed with custom path"""

    untyped_def_behavior: NotRequired[UntypedDefBehavior]
    """How to handle untyped function definitions (default: check-and-infer-return-type)"""

    infer_with_first_use: NotRequired[bool]
    """Infer container types from first usage patterns (default: true)"""

    ignore_errors_in_generated_code: NotRequired[bool]
    """Skip type checking for files containing @generated marker"""

    permissive_ignores: NotRequired[bool]
    """Respect ignore annotations from non-Pyrefly tools (e.g. # type: ignore)"""

    enabled_ignores: NotRequired[list[str]]
    """Tool ignore directives to recognize (default: ["type", "pyrefly"])"""

    # ========================================================================
    # IMPORT HANDLING
    # ========================================================================

    replace_imports_with_any: NotRequired[list[str]]
    """Module globs to unconditionally replace with typing.Any"""

    ignore_missing_imports: NotRequired[list[str]]
    """Module globs to replace with typing.Any when not found"""

    ignore_missing_source: NotRequired[bool]
    """Ignore missing source packages when only type stubs are available"""

    # ========================================================================
    # ERROR CONFIGURATION
    # ========================================================================

    errors: NotRequired[ErrorConfig]
    """Error severity configuration: {"error-code": bool, ...}"""
