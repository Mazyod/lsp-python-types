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
    assert cfg["strict"] is True  # pyright: ignore[reportTypedDictNotRequiredAccess]
