from __future__ import annotations

from pathlib import Path

import tomli_w

import lsp_types
from lsp_types import types
from lsp_types.process import ProcessLaunchInfo
from lsp_types.session import LSPBackend

from .config_schema import Model as PyreflyConfig


class PyreflyBackend(LSPBackend):
    """Pyrefly-specific LSP backend implementation"""

    def write_config(self, base_path: Path, options: PyreflyConfig) -> None:
        """
        Write pyrefly.toml configuration file.

        Accepts any mapping (including PyreflyConfig TypedDict and plain dicts
        with arbitrary fields). Field names are converted from snake_case to
        kebab-case to match Pyrefly's official TOML format.
        """
        # Convert snake_case keys to kebab-case for TOML file
        kebab_options = {key.replace("_", "-"): value for key, value in options.items()}

        config_path = base_path / "pyrefly.toml"
        toml_content = tomli_w.dumps(kebab_options)
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
