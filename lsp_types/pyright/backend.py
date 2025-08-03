from __future__ import annotations

import json
from pathlib import Path

import lsp_types
from lsp_types import types
from lsp_types.process import ProcessLaunchInfo
from lsp_types.session import LSPBackend

from .config_schema import Model as PyrightConfig


class PyrightBackend(LSPBackend):
    """Pyright-specific LSP backend implementation"""

    def write_config(self, base_path: Path, options: PyrightConfig) -> None:
        """Write pyrightconfig.json configuration file"""
        config_path = base_path / "pyrightconfig.json"
        config_path.write_text(json.dumps(options, indent=2))

    def create_process_launch_info(
        self, base_path: Path, options: PyrightConfig
    ) -> ProcessLaunchInfo:
        """Create process launch info for Pyright LSP server"""
        # NOTE: requires node and basedpyright to be installed and accessible
        return ProcessLaunchInfo(cmd=["pyright-langserver", "--stdio"], cwd=base_path)

    def get_lsp_capabilities(self) -> types.ClientCapabilities:
        """Get LSP client capabilities for Pyright"""
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
            }
        }

    def get_workspace_settings(
        self, options: PyrightConfig
    ) -> types.DidChangeConfigurationParams:
        """Get workspace settings for didChangeConfiguration"""
        return {"settings": options}
