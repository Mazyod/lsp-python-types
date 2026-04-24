from __future__ import annotations

from pathlib import Path

import tomli_w

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
        raise NotImplementedError  # Task 4

    def get_lsp_capabilities(self) -> types.ClientCapabilities:
        raise NotImplementedError  # Task 4

    def get_workspace_settings(
        self, options: ZubanConfig
    ) -> types.DidChangeConfigurationParams:
        raise NotImplementedError  # Task 4

    def get_semantic_tokens_legend(self) -> types.SemanticTokensLegend | None:
        raise NotImplementedError  # Task 4

    def requires_file_on_disk(self) -> bool:
        raise NotImplementedError  # Task 4
