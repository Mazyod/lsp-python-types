from __future__ import annotations

import tomllib
import typing as t
from pathlib import Path

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
        options
        | {"strict": True, "disallow_untyped_defs": True, "python_version": "3.12"},
    )
    backend.write_config(tmp_path, options)

    zuban = tomllib.loads((tmp_path / "pyproject.toml").read_text())["tool"]["zuban"]
    assert zuban["strict"] is True
    assert zuban["disallow_untyped_defs"] is True
    assert zuban["python_version"] == "3.12"


def test_zuban_backend_write_config_preserves_existing_pyproject(tmp_path: Path):
    """ZubanBackend.write_config must not destroy existing pyproject.toml content.

    Because `Session.create()` defaults `base_path=Path(".")`, a naive
    `Session.create(ZubanBackend())` call from a real project root must preserve
    the user's `[project]` metadata and other `[tool.*]` sections. This test pins
    the merge contract: everything survives except that `[tool.zuban]` is
    added/updated in place.
    """
    from lsp_types.zuban.backend import ZubanBackend

    pre_existing = (
        "[project]\n"
        'name = "someone-elses-project"\n'
        'version = "1.2.3"\n'
        "\n"
        "[tool.ruff]\n"
        "line-length = 88\n"
    )
    config_path = tmp_path / "pyproject.toml"
    config_path.write_text(pre_existing)

    backend = ZubanBackend()
    options: ZubanConfig = {"mode": "default"}
    backend.write_config(tmp_path, options)

    # Contract: existing sections survive; [tool.zuban] is added.
    parsed = tomllib.loads(config_path.read_text())
    assert parsed["project"]["name"] == "someone-elses-project"
    assert parsed["project"]["version"] == "1.2.3"
    assert parsed["tool"]["ruff"]["line-length"] == 88
    assert parsed["tool"]["zuban"] == {"mode": "default"}


def test_zuban_backend_write_config_replaces_existing_zuban_table(tmp_path: Path):
    """Re-invoking write_config replaces the previous [tool.zuban] table in place."""
    from lsp_types.zuban.backend import ZubanBackend

    backend = ZubanBackend()
    backend.write_config(tmp_path, {"mode": "mypy", "untyped_strict_optional": False})
    backend.write_config(tmp_path, {"mode": "default"})

    parsed = tomllib.loads((tmp_path / "pyproject.toml").read_text())
    # New call wins: mode flipped, prior untyped_strict_optional is gone.
    assert parsed["tool"]["zuban"] == {"mode": "default"}


def test_zuban_backend_create_process_launch_info_no_flags(tmp_path: Path):
    """Zuban's server subcommand takes no CLI flags."""
    from lsp_types.zuban.backend import ZubanBackend

    backend = ZubanBackend()
    proc_info = backend.create_process_launch_info(tmp_path, {})
    assert proc_info.cmd == ["zuban", "server"]
    assert proc_info.cwd == tmp_path


def test_zuban_backend_requires_file_on_disk_false():
    """Zuban supports virtual documents (confirmed by smoke test)."""
    from lsp_types.zuban.backend import ZubanBackend

    assert ZubanBackend().requires_file_on_disk() is False


def test_zuban_backend_semantic_tokens_legend_none():
    """Zuban advertises its legend via LSP; no hardcoded legend needed."""
    from lsp_types.zuban.backend import ZubanBackend

    assert ZubanBackend().get_semantic_tokens_legend() is None


def test_zuban_backend_lsp_capabilities_parity():
    """Capability set matches Pyrefly/ty parity (no extended features yet)."""
    import typing as t
    from lsp_types.zuban.backend import ZubanBackend
    from lsp_types import DiagnosticTag, MarkupKind

    caps = ZubanBackend().get_lsp_capabilities()
    td = t.cast(dict, caps.get("textDocument"))
    assert td is not None

    # Top-level keys required for parity.
    assert "publishDiagnostics" in td
    assert "hover" in td
    assert "signatureHelp" in td
    assert "completion" in td
    assert "definition" in td
    assert "references" in td
    assert "rename" in td

    # publishDiagnostics structure.
    pd = t.cast(dict, td["publishDiagnostics"])
    assert pd["versionSupport"] is True
    assert pd["tagSupport"]["valueSet"] == [
        DiagnosticTag.Unnecessary,
        DiagnosticTag.Deprecated,
    ]

    # hover structure.
    hover = t.cast(dict, td["hover"])
    assert hover["contentFormat"] == [
        MarkupKind.Markdown,
        MarkupKind.PlainText,
    ]


def test_zuban_backend_workspace_settings_passthrough():
    """get_workspace_settings wraps the options dict as {settings: options}."""
    from lsp_types.zuban.backend import ZubanBackend

    options: ZubanConfig = {"mode": "default", "untyped_strict_optional": True}
    settings = ZubanBackend().get_workspace_settings(options)
    assert settings == {"settings": options}
