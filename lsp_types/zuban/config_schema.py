# Zuban configuration schema
#
# Zuban reads configuration from `pyproject.toml` (under `[tool.zuban]` for
# native "default" mode, or `[tool.mypy]` for Mypy-compatible mode), as well
# as `mypy.ini`, `.mypy.ini`, and `setup.cfg`. This backend writes only
# `pyproject.toml` with a `[tool.zuban]` table using snake_case keys — the
# format Zuban's own documentation shows.
#
# Only Zuban-specific options are typed here. Mypy-compatible options
# (e.g. `strict`, `disallow_untyped_defs`, `python_version`) are accepted as
# arbitrary extra fields and pass through to the TOML file unchanged.
#
# Zuban has no published JSON schema, so this module is hand-written.

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

# Zuban's two operating modes. `default` is PyRight-like and recommended.
ZubanMode = Literal["default", "mypy"]

# Controls how Zuban infers untyped function return types.
# - `any`: behave like Mypy (return type is `Any`).
# - `inferred`: infer return types (Zuban default).
# - `advanced`: more sophisticated inference including parameter types.
UntypedFunctionReturnMode = Literal["any", "inferred", "advanced"]


class Model(TypedDict, total=False):
    """Zuban-specific configuration written under `[tool.zuban]` in pyproject.toml.

    The typed fields below cover Zuban-specific options. Mypy-compatible options
    (e.g. `strict`, `disallow_untyped_defs`, `python_version`) are not in the
    TypedDict, but can be supplied at call sites via `typing.cast` — they pass
    through to the TOML file unchanged.
    """

    mode: NotRequired[ZubanMode]
    """Selects `default` (PyRight-like, recommended) or `mypy` (Mypy-compatible)."""

    mypy_path: NotRequired[list[str]]
    """Additional import search paths (equivalent to Mypy's `mypy_path` / `MYPYPATH`)."""

    untyped_strict_optional: NotRequired[bool]
    """Enable strict Optional checks in untyped contexts. Default in Zuban: True."""

    untyped_function_return_mode: NotRequired[UntypedFunctionReturnMode]
    """How untyped function return types are handled. Default in Zuban: `inferred`."""
