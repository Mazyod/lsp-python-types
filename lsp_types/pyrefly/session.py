from __future__ import annotations

import typing as t
from pathlib import Path

import lsp_types
from lsp_types.pool import LSPProcessPool
from lsp_types.process import LSPProcess, ProcessLaunchInfo

from .config_schema import Model as PyreflyConfig


class PyreflySession(lsp_types.Session):
    """
    Pyrefly LSP session implementation with process pooling support.
    
    Pyrefly is Facebook's fast Python type checker written in Rust with built-in LSP support.
    """

    @classmethod
    async def create(
        cls,
        *,
        base_path: Path = Path("."),
        initial_code: str = "",
        options: PyreflyConfig = {},
        pool: LSPProcessPool | None = None,
    ) -> t.Self:
        """Create a new Pyrefly session using a process pool."""
        base_path = base_path.resolve()
        base_path_str = str(base_path)

        # Create pyrefly.toml config file (Pyrefly's configuration format)
        config_path = base_path / "pyrefly.toml"
        
        # Convert options to TOML format (basic implementation)
        # Note: Pyrefly's config format is still evolving, so we keep it minimal
        toml_content = ""
        if options.get("verbose"):
            toml_content += "verbose = true\n"
        if "threads" in options and options["threads"] is not None:
            toml_content += f"threads = {options['threads']}\n"
        if "color" in options:
            toml_content += f"color = \"{options['color']}\"\n"
        if "indexing_mode" in options:
            toml_content += f"indexing-mode = \"{options['indexing_mode']}\"\n"
        
        config_path.write_text(toml_content)

        async def create_lsp_process():
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
            proc_info = ProcessLaunchInfo(cmd=cmd_args)
            lsp_process = LSPProcess(proc_info)
            await lsp_process.start()

            # Initialize LSP connection with capabilities similar to Pyright
            await lsp_process.send.initialize(
                {
                    "processId": None,
                    "rootUri": f"file://{base_path}",
                    "rootPath": base_path_str,
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
                            "completion": {},
                            "definition": {},
                            "references": {},
                        }
                    },
                }
            )

            # Pyrefly requires initialized event
            await lsp_process.notify.initialized({})

            return lsp_process

        # Use pool if provided, otherwise create a default non-pooling pool
        if pool is None:
            pool = LSPProcessPool(max_size=0)  # No recycling, immediate shutdown

        lsp_process = await pool.acquire(create_lsp_process, base_path_str)
        pyrefly_session = cls(lsp_process, pool=pool)

        # Update settings via didChangeConfiguration
        # Pyrefly might not support all workspace configuration changes yet
        await lsp_process.notify.workspace_did_change_configuration(
            {"settings": options}
        )

        # Simulate opening a document
        await pyrefly_session._open_document(initial_code)

        return pyrefly_session

    def __init__(
        self,
        lsp_process: LSPProcess,
        *,
        pool: LSPProcessPool,
    ):
        self._process = lsp_process
        self._document_uri = "file:///test.py"
        self._document_version = 1
        self._document_text = ""

        self._pool = pool

    # region - Session methods

    async def shutdown(self) -> None:
        """Shutdown and recycle the session back to the pool"""
        if self._pool is None:
            return  # Already recycled

        # Release back to pool (document cleanup handled by pool/process reset)
        # For max_size=0 pools, this will immediately shutdown the process
        await self._pool.release(self._process)

        # Clear references to prevent further use
        self._pool = None

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
        # As a bare minimum, cache the diagnostics per document version
        # When diagnostics are requested twice, it would hang otherwise
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
        self._document_text = code
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
        # Track the opened document
        self._process.track_document_open(self._document_uri)