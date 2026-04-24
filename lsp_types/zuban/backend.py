from __future__ import annotations

from pathlib import Path

import tomli_w

import lsp_types
from lsp_types import types
from lsp_types.process import ProcessLaunchInfo
from lsp_types.session import LSPBackend

from .config_schema import Model as ZubanConfig


class ZubanBackend(LSPBackend):
    """Zuban-specific LSP backend implementation."""

    def write_config(self, base_path: Path, options: ZubanConfig) -> None:
        """Write pyproject.toml with a [tool.zuban] table.

        Keys stay snake_case — Zuban's native TOML format uses snake_case directly
        (unlike Pyrefly/ty which use kebab-case). Presence of `[tool.zuban]` puts
        Zuban into its recommended `default` mode.
        """
        config_path = base_path / "pyproject.toml"
        toml_content = tomli_w.dumps({"tool": {"zuban": dict(options)}})
        config_path.write_text(toml_content)

    def create_process_launch_info(
        self, base_path: Path, options: ZubanConfig
    ) -> ProcessLaunchInfo:
        # `zuban server` takes no CLI flags; all configuration is file-based.
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
