from __future__ import annotations

from pathlib import Path

import tomlkit

import lsp_types
from lsp_types import types
from lsp_types.process import ProcessLaunchInfo
from lsp_types.session import LSPBackend

from .config_schema import Model as ZubanConfig


class ZubanBackend(LSPBackend):
    """Zuban-specific LSP backend implementation."""

    def write_config(self, base_path: Path, options: ZubanConfig) -> None:
        """Add or update `[tool.zuban]` in `pyproject.toml`, preserving other content.

        Zuban's native-mode config lives under `[tool.zuban]` in `pyproject.toml`
        — it has no dedicated config file. Because `Session.create()` defaults
        `base_path=Path(".")`, this method must not destroy a caller's existing
        `pyproject.toml`. It is a format-preserving edit via `tomlkit`: only the
        `[tool.zuban]` table is added or replaced. Comments, inline tables,
        arrays-of-tables, key ordering, whitespace and line endings elsewhere in
        the file survive. Comments tomlkit associates with an existing
        `[tool.zuban]` go with it, since that table is replaced wholesale.

        Keys stay snake_case — Zuban's native TOML format uses snake_case directly
        (unlike Pyrefly/ty which use kebab-case). Presence of `[tool.zuban]` puts
        Zuban into its recommended `default` mode.
        """
        config_path = base_path / "pyproject.toml"
        if config_path.exists():
            # newline="" keeps the file's own line endings intact; Path.read_text
            # would normalise CRLF to LF and rewrite every line.
            with config_path.open("r", newline="") as handle:
                document = tomlkit.parse(handle.read())
        else:
            document = tomlkit.document()

        if "tool" not in document:
            document["tool"] = tomlkit.table(is_super_table=True)
        # Assign the plain dict rather than a pre-built tomlkit item: tomlkit
        # then converts it to match the parent, so an inline `tool = { ... }`
        # table gets an inline child instead of raising.
        document["tool"]["zuban"] = dict(options)  # type: ignore[index]

        with config_path.open("w", newline="") as handle:
            handle.write(tomlkit.dumps(document))

    def create_process_launch_info(
        self, base_path: Path, options: ZubanConfig
    ) -> ProcessLaunchInfo:
        # `zuban server` takes no CLI flags. Config comes from pyproject.toml's
        # [tool.zuban] table, or from initializationOptions at LSP initialization.
        return ProcessLaunchInfo(cmd=["zuban", "server"], cwd=base_path)

    def get_lsp_capabilities(self) -> types.ClientCapabilities:
        return {
            "textDocument": {
                "publishDiagnostics": {
                    "versionSupport": True,
                    "tagSupport": {
                        "valueSet": [
                            lsp_types.DiagnosticTag.Unnecessary,
                            lsp_types.DiagnosticTag.Deprecated,
                        ]
                    },
                },
                "hover": {
                    "contentFormat": [
                        lsp_types.MarkupKind.Markdown,
                        lsp_types.MarkupKind.PlainText,
                    ],
                },
                "signatureHelp": {},
                "completion": {},
                "definition": {},
                "references": {},
                "rename": {},
            }
        }

    def get_workspace_settings(
        self, options: ZubanConfig
    ) -> types.DidChangeConfigurationParams:
        return {"settings": options}

    def get_semantic_tokens_legend(self) -> types.SemanticTokensLegend | None:
        # Zuban advertises its legend via the initialize response.
        return None

    def requires_file_on_disk(self) -> bool:
        # Confirmed in smoke test: virtual documents (didOpen without disk file) work.
        return False

    def consumes_did_change_configuration(self) -> bool:
        # Zuban reads `[tool.zuban]` from pyproject.toml; the notification is
        # logged as an unhandled-notification error otherwise.
        return False
