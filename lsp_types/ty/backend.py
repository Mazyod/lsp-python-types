from __future__ import annotations

import typing as t
from pathlib import Path

import tomli_w

import lsp_types
from lsp_types import types
from lsp_types.process import ProcessLaunchInfo
from lsp_types.session import LSPBackend

from .config_schema import Model as TyConfig


def _convert_keys_to_kebab(obj: t.Mapping[str, t.Any]) -> dict[str, t.Any]:
    """
    Recursively convert dict keys from snake_case to kebab-case.

    ty uses kebab-case keys in its TOML configuration files (e.g., python-version,
    extra-paths). This function converts Python-style snake_case keys to the
    required kebab-case format, handling nested dictionaries and lists.

    Args:
        obj: Dictionary with snake_case keys

    Returns:
        New dictionary with kebab-case keys, recursively converted
    """
    result: dict[str, t.Any] = {}
    for key, value in obj.items():
        kebab_key = key.replace("_", "-")
        if isinstance(value, dict):
            result[kebab_key] = _convert_keys_to_kebab(value)
        elif isinstance(value, list):
            result[kebab_key] = [
                _convert_keys_to_kebab(v) if isinstance(v, dict) else v for v in value
            ]
        else:
            result[kebab_key] = value
    return result


class TyBackend(LSPBackend):
    """ty-specific LSP backend implementation"""

    def write_config(self, base_path: Path, options: TyConfig) -> None:
        """
        Write ty.toml configuration file.

        Accepts any mapping (including TyConfig TypedDict and plain dicts
        with arbitrary fields). Field names are recursively converted from
        snake_case to kebab-case to match ty's official TOML format.

        Unlike Pyrefly's flat config structure, ty uses nested TOML sections
        (e.g., [environment], [src], [rules]), requiring recursive conversion.
        """
        # Convert snake_case keys to kebab-case for TOML file (recursive)
        kebab_options = _convert_keys_to_kebab(dict(options))

        config_path = base_path / "ty.toml"
        toml_content = tomli_w.dumps(kebab_options)
        config_path.write_text(toml_content)

    def create_process_launch_info(
        self, base_path: Path, options: TyConfig
    ) -> ProcessLaunchInfo:
        """Create process launch info for ty LSP server"""
        # ty server command is simple: just "ty server"
        # Unlike Pyrefly, ty server accepts no CLI flags - all config via ty.toml
        cmd = ["ty", "server"]

        # NOTE: requires ty to be installed and accessible
        return ProcessLaunchInfo(cmd=cmd, cwd=base_path)

    def get_lsp_capabilities(self) -> types.ClientCapabilities:
        """Get LSP client capabilities for ty"""
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
        self, options: TyConfig
    ) -> types.DidChangeConfigurationParams:
        """Get workspace settings for didChangeConfiguration"""
        return {"settings": options}
