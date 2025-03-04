from __future__ import annotations

import json
import typing as t
from pathlib import Path

import lsp_types
from lsp_types.process import LSPProcess, ProcessLaunchInfo

from .config_schema import Model as PyrightConfig


class PyrightSession(lsp_types.Session):
    """
    Pyright LSP session implementation.
    TODO: Move process initialization and config_path within the session instance
    """

    @classmethod
    async def create(
        cls,
        *,
        base_path: Path = Path("."),
        initial_code: str = "",
        options: PyrightConfig = {},
    ) -> t.Self:
        """Create a new Pyright session"""
        base_path = base_path.resolve()

        config_path = base_path / "pyrightconfig.json"
        config_path.write_text(json.dumps(options, indent=2))

        # NOTE: requires node and basedpyright to be installed and accessible
        proc_info = ProcessLaunchInfo(cmd=["pyright-langserver", "--stdio"])
        lsp_process = LSPProcess(proc_info)
        await lsp_process.start()

        # TODO: ability to configure these options
        await lsp_process.send.initialize(
            {
                "processId": None,
                "rootUri": f"file://{base_path}",
                "rootPath": str(base_path),
                "capabilities": {
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
                },
            }
        )

        # Update settings via didChangeConfiguration
        await lsp_process.notify.workspace_did_change_configuration({"settings": {}})

        pyright_session = cls(lsp_process)

        # Simulate opening a document
        await pyright_session._open_document(initial_code)

        return pyright_session

    def __init__(self, lsp_process: LSPProcess):
        self._process = lsp_process
        self._document_uri = "file:///test.py"
        self._document_version = 1
        self._document_text = ""

    # region - Session methods

    async def shutdown(self) -> None:
        """Shutdown the session"""
        await self._process.stop()

    async def update_code(self, code: str) -> int:
        """Update the code in the current document"""
        self._document_version += 1
        self._document_text = code

        document_version = self._document_version
        await self._process.notify.did_change_text_document(
            {
                "textDocument": {
                    "uri": self._document_uri,
                    "version": self._document_version,
                },
                "contentChanges": [{"text": code}],
            }
        )

        return document_version

    async def get_diagnostics(self):
        """Get diagnostics for the given code"""
        # FIXME: riddled with race conditions
        return await self._process.notify.on_publish_diagnostics()

    async def get_hover_info(
        self, position: lsp_types.Position
    ) -> lsp_types.Hover | None:
        """Get hover information at the given position"""
        return await self._process.send.hover(
            {"textDocument": {"uri": self._document_uri}, "position": position}
        )

    async def get_rename_edits(
        self, position: lsp_types.Position, new_name: str
    ) -> lsp_types.WorkspaceEdit | None:
        """Get rename edits for the given position"""
        return await self._process.send.rename(
            {
                "textDocument": {"uri": self._document_uri},
                "position": position,
                "newName": new_name,
            }
        )

    async def get_signature_help(
        self, position: lsp_types.Position
    ) -> lsp_types.SignatureHelp | None:
        """Get signature help at the given position"""
        return await self._process.send.signature_help(
            {"textDocument": {"uri": self._document_uri}, "position": position}
        )

    async def get_completion(
        self, position: lsp_types.Position
    ) -> lsp_types.CompletionList | list[lsp_types.CompletionItem] | None:
        """Get completion items at the given position"""
        return await self._process.send.completion(
            {"textDocument": {"uri": self._document_uri}, "position": position}
        )

    async def resolve_completion(
        self, completion_item: lsp_types.CompletionItem
    ) -> lsp_types.CompletionItem:
        """Resolve the given completion item"""
        return await self._process.send.resolve_completion_item(completion_item)

    async def get_semantic_tokens(self) -> lsp_types.SemanticTokens | None:
        """Get semantic tokens for the current document"""
        return await self._process.send.semantic_tokens_full(
            {"textDocument": {"uri": self._document_uri}}
        )

    # endregion

    # Private methods

    async def _open_document(self, code: str) -> None:
        """Open a document with the given code"""
        await self._process.notify.did_open_text_document(
            {
                "textDocument": {
                    "languageId": lsp_types.LanguageKind.Python,
                    "version": self._document_version,
                    "uri": self._document_uri,
                    "text": code,
                }
            }
        )
