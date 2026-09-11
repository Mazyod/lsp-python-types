# Pyrefly configuration schema
# Based on official Pyrefly documentation: https://pyrefly.org/en/docs/configuration/
# CLI reference: https://github.com/facebook/pyrefly
# Reviewed against Pyrefly 1.3.0 (2026-09-11).
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

ErrorSeverity = Literal["error", "warn", "info", "ignore"]
# Boolean values remain accepted by Pyrefly for compatibility.
ErrorConfig = dict[str, bool | ErrorSeverity]


class Model(TypedDict):
    """
    Pyrefly Configuration Schema

    Common Pyrefly configuration options and backend launch settings.
    Field names use snake_case; the backend writes kebab-case TOML keys.

    All fields are NotRequired for maximum flexibility. For arbitrary fields
    not yet in this schema:
    pass a plain dictionary to Session.create(options=...).

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

    python_platform: NotRequired[str | list[str]]
    """One platform, multiple platforms, or "all" for sys.platform checks."""

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

    preset: NotRequired[Literal["off", "basic", "legacy", "default", "strict", "all"]]
    """Select the starting set of diagnostics and checking behavior."""

    untyped_def_behavior: NotRequired[UntypedDefBehavior]
    """Deprecated upstream; use check_unannotated_defs and infer_return_types."""

    check_unannotated_defs: NotRequired[bool]
    """Check unannotated function bodies (default: true with the default preset)."""

    infer_return_types: NotRequired[Literal["never", "annotated", "checked"]]
    """Infer returns for no functions, annotated functions, or all checked functions."""

    treat_all_caps_as_final: NotRequired[bool]
    """Reject reassignment of ALL_CAPS names (opt-in)."""

    required_version: NotRequired[str]
    """PEP 440 constraint on the Pyrefly version, e.g. ">=1.3,<1.4"."""

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

    replace_untyped_imports_with_any: NotRequired[list[str]]
    """Replace matching installed packages lacking stubs or py.typed with Any."""

    ignore_missing_imports: NotRequired[list[str]]
    """Module globs to replace with typing.Any when not found"""

    ignore_missing_source: NotRequired[bool]
    """Ignore missing source packages when only type stubs are available"""

    # ========================================================================
    # ERROR CONFIGURATION
    # ========================================================================

    errors: NotRequired[ErrorConfig]
    """Error code to severity (or legacy enabled/disabled boolean)."""

    baseline: NotRequired[str]
    """Path to a baseline file of existing diagnostics."""

    baseline_error_level: NotRequired[ErrorSeverity]
    """Severity for diagnostics matching the baseline (default: ignore)."""

    baseline_matching_mode: NotRequired[Literal["column", "concise-description"]]
    """Match baseline entries by source column or concise diagnostic description."""

    baseline_format: NotRequired[Literal["full", "minimal"]]
    """Amount of metadata written to baseline entries."""
