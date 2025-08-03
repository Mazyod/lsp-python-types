from __future__ import annotations

from pathlib import Path

import lsp_types
from lsp_types import types
from lsp_types.process import ProcessLaunchInfo
from lsp_types.session import LSPBackend

from .config_schema import Model as PyreflyConfig


class PyreflyBackend(LSPBackend):
    """Pyrefly-specific LSP backend implementation"""

    def write_config(self, base_path: Path, options: PyreflyConfig) -> None:
        """Write pyrefly.toml configuration file"""
        config_path = base_path / "pyrefly.toml"

        # Convert options to TOML format (basic implementation)
        # Note: Pyrefly's config format is still evolving, so we keep it minimal
        toml_content = ""
        if options.get("verbose"):
            toml_content += "verbose = true\n"
        if "threads" in options and options["threads"] is not None:
            toml_content += f"threads = {options['threads']}\n"
        if "color" in options:
            toml_content += f'color = "{options["color"]}"\n'
        if "indexing_mode" in options:
            toml_content += f'indexing-mode = "{options["indexing_mode"]}"\n'

        config_path.write_text(toml_content)

    def create_process_launch_info(
        self, base_path: Path, options: PyreflyConfig
    ) -> ProcessLaunchInfo:
        """Create process launch info for Pyrefly LSP server"""
        # Build command args for Pyrefly LSP server
        cmd_args = ["pyrefly", "lsp"]

        # Add CLI options based on configuration
        if options.get("verbose"):
            cmd_args.append("--verbose")
        if "threads" in options and options["threads"] is not None:
            cmd_args.extend(["--threads", str(options["threads"])])
        if "indexing_mode" in options:
            cmd_args.extend(["--indexing-mode", options["indexing_mode"]])

        # NOTE: requires pyrefly to be installed and accessible
        return ProcessLaunchInfo(cmd=cmd_args, cwd=base_path)

    def get_lsp_capabilities(self) -> types.ClientCapabilities:
        """Get LSP client capabilities for Pyrefly"""
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
            }
        }

    def get_workspace_settings(
        self, options: PyreflyConfig
    ) -> types.DidChangeConfigurationParams:
        """Get workspace settings for didChangeConfiguration"""
        return {"settings": options}
