from __future__ import annotations

import dataclasses as dc
import typing as t
from pathlib import Path

from . import types
from .pool import LSPProcessPool
from .process import LSPProcess, ProcessLaunchInfo


class LSPBackend(t.Protocol):
    """Protocol defining backend-specific LSP operations"""

    def write_config(self, base_path: Path, options: t.Mapping) -> None:
        """Write backend-specific configuration file"""
        ...

    def create_process_launch_info(
        self, base_path: Path, options: t.Mapping
    ) -> ProcessLaunchInfo:
        """Create process launch info for the LSP server"""
        ...

    def get_lsp_capabilities(self) -> types.ClientCapabilities:
        """Get LSP client capabilities"""
        ...

    def get_workspace_settings(
        self, options: t.Mapping
    ) -> types.DidChangeConfigurationParams:
        """Get workspace settings for didChangeConfiguration"""
        ...


@dc.dataclass(kw_only=True)
class DiagnosticsResult:
    id: str
    value: list[types.Diagnostic]


class Session:
    """Concrete LSP session implementation using pluggable backends"""

    @classmethod
    async def create(
        cls,
        backend: LSPBackend,
        *,
        base_path: Path = Path("."),
        initial_code: str = "",
        options: t.Mapping = {},
        pool: LSPProcessPool | None = None,
    ) -> t.Self:
        """Create a new LSP session using the provided backend"""
        base_path = base_path.resolve()
        base_path_str = str(base_path)

        # Write backend-specific configuration
        backend.write_config(base_path, options)

        async def create_lsp_process():
            proc_info = backend.create_process_launch_info(base_path, options)
            lsp_process = LSPProcess(proc_info)
            await lsp_process.start()

            # Initialize LSP connection
            await lsp_process.send.initialize(
                {
                    "processId": None,
                    "rootUri": f"file://{base_path}",
                    "rootPath": base_path_str,
                    "capabilities": backend.get_lsp_capabilities(),
                }
            )

            # Send initialized notification (required by LSP spec)
            await lsp_process.notify.initialized({})

            return lsp_process

        # Use pool if provided, otherwise create a default non-pooling pool
        if pool is None:
            pool = LSPProcessPool(max_size=0)  # No recycling, immediate shutdown

        lsp_process = await pool.acquire(create_lsp_process, base_path_str)
        session = cls(lsp_process, backend, base_path, pool=pool)

        # Update settings via didChangeConfiguration
        workspace_settings = backend.get_workspace_settings(options)
        await lsp_process.notify.workspace_did_change_configuration(workspace_settings)

        # Simulate opening a document
        await session._open_document(initial_code)

        return session

    def __init__(
        self,
        lsp_process: LSPProcess,
        backend: LSPBackend,
        base_path: Path,
        *,
        pool: LSPProcessPool,
    ):
        self._process = lsp_process
        self._backend = backend
        self._document_uri = f"file://{base_path / 'new.py'}"
        self._document_version = 1
        self._document_text = ""
        self._active_pool: LSPProcessPool | None = pool
        self._diag_result: DiagnosticsResult | None = None

    async def shutdown(self) -> None:
        """Shutdown and recycle the session back to the pool"""
        if self._active_pool is None:
            return  # Already recycled

        # Release back to pool (document cleanup handled by pool/process reset)
        # For max_size=0 pools, this will immediately shutdown the process
        await self._active_pool.release(self._process)

        # Clear references to prevent further use
        self._active_pool = None

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

    async def get_diagnostics(self) -> list[types.Diagnostic]:
        """Pull diagnostics via textDocument/diagnostic (LSP-3.17)"""
        params: types.DocumentDiagnosticParams = {
            "textDocument": {"uri": self._document_uri},
        }

        if result := self._diag_result:
            params["previousResultId"] = result.id

        report = await self._process.send.text_document_diagnostic(params)

        diagnostics: list[types.Diagnostic]
        match report["kind"]:
            case "full":
                diagnostics = report["items"]
            case "unchanged":
                diagnostics = self._diag_result.value if self._diag_result else []

        # Persist token for the next delta request (if present)
        if result_id := report.get("resultId"):
            self._diag_result = DiagnosticsResult(id=result_id, value=diagnostics)

        # For 'unchanged' nothing is appended ⇒ return cached view if desired
        return diagnostics

    async def get_hover_info(self, position: types.Position) -> types.Hover | None:
        """Get hover information at the given position"""
        return await self._process.send.hover(
            {"textDocument": {"uri": self._document_uri}, "position": position}
        )

    async def get_rename_edits(
        self, position: types.Position, new_name: str
    ) -> types.WorkspaceEdit | None:
        """Get rename edits for the given position"""
        return await self._process.send.rename(
            {
                "textDocument": {"uri": self._document_uri},
                "position": position,
                "newName": new_name,
            }
        )

    async def get_signature_help(
        self, position: types.Position
    ) -> types.SignatureHelp | None:
        """Get signature help at the given position"""
        return await self._process.send.signature_help(
            {"textDocument": {"uri": self._document_uri}, "position": position}
        )

    async def get_completion(
        self, position: types.Position
    ) -> types.CompletionList | list[types.CompletionItem] | None:
        """Get completion items at the given position"""
        return await self._process.send.completion(
            {"textDocument": {"uri": self._document_uri}, "position": position}
        )

    async def resolve_completion(
        self, completion_item: types.CompletionItem
    ) -> types.CompletionItem:
        """Resolve the given completion item"""
        return await self._process.send.resolve_completion_item(completion_item)

    async def get_semantic_tokens(self) -> types.SemanticTokens | None:
        """Get semantic tokens for the current document"""
        return await self._process.send.semantic_tokens_full(
            {"textDocument": {"uri": self._document_uri}}
        )

    # Private methods

    async def _open_document(self, code: str) -> None:
        """Open a document with the given code"""
        self._document_text = code
        await self._process.notify.did_open_text_document(
            {
                "textDocument": {
                    "languageId": types.LanguageKind.Python,
                    "version": self._document_version,
                    "uri": self._document_uri,
                    "text": code,
                }
            }
        )
        # Track the opened document
        self._process.track_document_open(self._document_uri)
