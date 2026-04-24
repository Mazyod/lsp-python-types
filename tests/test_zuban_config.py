from __future__ import annotations

import typing as t

from lsp_types.zuban.config_schema import Model as ZubanConfig


def test_zuban_config_minimal_instance():
    """An empty ZubanConfig is valid (all fields optional)."""
    cfg: ZubanConfig = {}
    assert cfg == {}


def test_zuban_config_accepts_known_fields():
    """ZubanConfig accepts the four Zuban-specific options."""
    cfg: ZubanConfig = {
        "mode": "default",
        "mypy_path": ["./src", "./lib"],
        "untyped_strict_optional": True,
        "untyped_function_return_mode": "inferred",
    }
    assert cfg["mode"] == "default"
    assert cfg["mypy_path"] == ["./src", "./lib"]
    assert cfg["untyped_strict_optional"] is True
    assert cfg["untyped_function_return_mode"] == "inferred"


def test_zuban_config_accepts_arbitrary_fields_via_cast():
    """Mypy-compatible options not in the TypedDict still pass through at runtime."""
    cfg: ZubanConfig = {"mode": "default"}
    cfg = t.cast(
        ZubanConfig,
        cfg | {"strict": True, "disallow_untyped_defs": True, "python_version": "3.12"},
    )
    assert cfg["strict"] is True  # pyright: ignore[reportGeneralTypeIssues]
    assert cfg["disallow_untyped_defs"] is True  # pyright: ignore[reportGeneralTypeIssues]
    assert cfg["python_version"] == "3.12"  # pyright: ignore[reportGeneralTypeIssues]


import tomllib
from pathlib import Path


def test_zuban_backend_write_config_creates_pyproject_toml(tmp_path: Path):
    """ZubanBackend.write_config writes pyproject.toml with [tool.zuban] table."""
    from lsp_types.zuban.backend import ZubanBackend

    backend = ZubanBackend()
    options: ZubanConfig = {
        "mode": "default",
        "untyped_strict_optional": True,
    }
    backend.write_config(tmp_path, options)

    config_path = tmp_path / "pyproject.toml"
    assert config_path.exists(), "Expected pyproject.toml to be created"

    parsed = tomllib.loads(config_path.read_text())
    assert "tool" in parsed
    assert "zuban" in parsed["tool"]
    assert parsed["tool"]["zuban"]["mode"] == "default"
    assert parsed["tool"]["zuban"]["untyped_strict_optional"] is True


def test_zuban_backend_write_config_preserves_snake_case_keys(tmp_path: Path):
    """Snake_case keys must be preserved (no kebab-case conversion)."""
    from lsp_types.zuban.backend import ZubanBackend

    backend = ZubanBackend()
    options: ZubanConfig = {
        "mypy_path": ["./src"],
        "untyped_function_return_mode": "inferred",
    }
    backend.write_config(tmp_path, options)

    parsed = tomllib.loads((tmp_path / "pyproject.toml").read_text())
    zuban = parsed["tool"]["zuban"]
    assert "mypy_path" in zuban, "mypy_path must stay snake_case (no kebab conversion)"
    assert "mypy-path" not in zuban
    assert zuban["mypy_path"] == ["./src"]
    assert zuban["untyped_function_return_mode"] == "inferred"


def test_zuban_backend_write_config_allows_arbitrary_fields(tmp_path: Path):
    """Arbitrary (Mypy-compatible) fields pass through unchanged."""
    import typing as t
    from lsp_types.zuban.backend import ZubanBackend

    backend = ZubanBackend()
    options: ZubanConfig = {"mode": "default"}
    options = t.cast(
        ZubanConfig,
        options | {"strict": True, "disallow_untyped_defs": True, "python_version": "3.12"},
    )
    backend.write_config(tmp_path, options)

    zuban = tomllib.loads((tmp_path / "pyproject.toml").read_text())["tool"]["zuban"]
    assert zuban["strict"] is True
    assert zuban["disallow_untyped_defs"] is True
    assert zuban["python_version"] == "3.12"
