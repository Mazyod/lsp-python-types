# ty configuration schema
# Based on official ty documentation: https://docs.astral.sh/ty/reference/configuration/
#
# Note: Field names use snake_case (Python convention) but are automatically
# converted to kebab-case when written to ty.toml (official format).

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

# Rule severity levels
RuleSeverity = Literal["ignore", "warn", "error"]

# Platform options
PythonPlatform = Literal["win32", "darwin", "android", "ios", "linux", "all"]

# Output format options
OutputFormat = Literal["full", "concise"]


class EnvironmentConfig(TypedDict, total=False):
    """
    Python environment configuration.

    Controls how ty resolves Python modules and which Python version/platform
    to target for type checking.
    """

    extra_paths: NotRequired[list[str]]
    """User-provided module search paths for import resolution."""

    python: NotRequired[str]
    """Path to your project's Python environment or interpreter."""

    python_platform: NotRequired[PythonPlatform | str]
    """Target platform for sys.platform checks (e.g., 'linux', 'darwin', 'win32')."""

    python_version: NotRequired[str]
    """Python version to target (e.g., '3.12'). Default: 3.14."""

    root: NotRequired[list[str]]
    """Root paths of the project, used for finding first-party modules."""

    typeshed: NotRequired[str]
    """Optional path to a typeshed directory on disk."""


class SrcConfig(TypedDict, total=False):
    """
    Source file selection configuration.

    Controls which files ty includes or excludes from type checking.
    """

    include: NotRequired[list[str]]
    """Files and directories to type check."""

    exclude: NotRequired[list[str]]
    """Files and directories to skip. Supports gitignore-style patterns."""

    respect_ignore_files: NotRequired[bool]
    """Auto-exclude files listed in .gitignore. Default: true."""


class AnalysisConfig(TypedDict, total=False):
    """
    Analysis behavior configuration.

    Controls how ty performs type analysis.
    """

    respect_type_ignore_comments: NotRequired[bool]
    """Whether 'type: ignore' comments suppress errors. Default: true."""


class TerminalConfig(TypedDict, total=False):
    """
    Terminal output configuration.

    Controls how ty formats output when run from the command line.
    """

    error_on_warning: NotRequired[bool]
    """Exit with code 1 when warnings are emitted. Default: false."""

    output_format: NotRequired[OutputFormat]
    """Diagnostic message format: 'full' or 'concise'. Default: full."""


class OverrideConfig(TypedDict, total=False):
    """
    Per-file override configuration.

    Allows applying different rules to specific files or directories.
    """

    include: NotRequired[list[str]]
    """Glob patterns for files to affect."""

    exclude: NotRequired[list[str]]
    """Glob patterns to exclude from this override."""

    rules: NotRequired[dict[str, RuleSeverity]]
    """Rule overrides for matched files."""


class Model(TypedDict, total=False):
    """
    ty Configuration Schema

    Comprehensive type definitions for all ty configuration options.
    Field names use snake_case following Python conventions but are
    automatically converted to kebab-case when written to ty.toml.

    Official Documentation: https://docs.astral.sh/ty/reference/configuration/
    """

    # ========================================================================
    # RULES CONFIGURATION
    # ========================================================================

    rules: NotRequired[dict[str, RuleSeverity]]
    """
    Rule severity configuration.

    Maps rule names to severity levels: 'ignore', 'warn', or 'error'.
    Example: {"possibly-unresolved-reference": "error", "unused-ignore-comment": "warn"}
    """

    # ========================================================================
    # SECTION CONFIGURATIONS
    # ========================================================================

    analysis: NotRequired[AnalysisConfig]
    """Analysis behavior settings."""

    environment: NotRequired[EnvironmentConfig]
    """Python environment settings."""

    src: NotRequired[SrcConfig]
    """Source file selection settings."""

    terminal: NotRequired[TerminalConfig]
    """Terminal output settings."""

    overrides: NotRequired[list[OverrideConfig]]
    """Per-file configuration overrides."""
