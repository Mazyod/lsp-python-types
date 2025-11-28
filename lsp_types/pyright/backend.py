from __future__ import annotations

import json
import shutil
from pathlib import Path

import lsp_types
from lsp_types import types
from lsp_types.process import ProcessLaunchInfo
from lsp_types.session import LSPBackend

from .config_schema import Model as PyrightConfig


class PyrightBackend(LSPBackend):
    """Pyright-specific LSP backend implementation"""

    def __init__(self, *, node_flags: list[str] | None = None):
        """
        Initialize PyrightBackend.

        Args:
            node_flags: Optional list of node flags to pass when launching the server.
                       If provided, pyright-langserver will be launched via node with these flags.
                       Example: ['--prof'] for profiling, ['--cpu-prof'] for CPU profiling.
        """
        self._node_flags = node_flags or []

    def write_config(self, base_path: Path, options: PyrightConfig) -> None:
        """Write pyrightconfig.json configuration file"""
        config_path = base_path / "pyrightconfig.json"
        config_path.write_text(json.dumps(options, indent=2))

    def create_process_launch_info(
        self, base_path: Path, options: PyrightConfig
    ) -> ProcessLaunchInfo:
        """Create process launch info for Pyright LSP server"""
        # NOTE: requires node and basedpyright to be installed and accessible
        if self._node_flags:
            # Launch via node with specified flags
            langserver_path = shutil.which("pyright-langserver")
            if not langserver_path:
                raise RuntimeError(
                    "pyright-langserver not found in PATH. "
                    "Please ensure it is installed and accessible."
                )
            cmd = ["node", *self._node_flags, langserver_path, "--stdio"]
        else:
            # Direct invocation (default behavior)
            cmd = ["pyright-langserver", "--stdio"]

        return ProcessLaunchInfo(cmd=cmd, cwd=base_path)

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
