import typing as t

from . import types


class Session(t.Protocol):
    """Protocol defining the interface for LSP sessions"""

    async def shutdown(self) -> None:
        """Shutdown the session"""
        ...

    async def update_code(self, code: str) -> int:
        """Update the code in the current document"""
        ...

    async def get_diagnostics(self) -> types.PublishDiagnosticsParams:
        """Get diagnostics for the current document"""
        ...

    async def get_hover_info(self, position: types.Position) -> types.Hover | None:
        """Get hover information at the given position"""
        ...

    async def get_rename_edits(
        self, position: types.Position, new_name: str
    ) -> types.WorkspaceEdit | None:
        """Get rename edits for the given position"""
        ...

    async def get_signature_help(
        self, position: types.Position
    ) -> types.SignatureHelp | None:
        """Get signature help at the given position"""
        ...

    async def get_completion(
        self, position: types.Position
    ) -> types.CompletionList | list[types.CompletionItem] | None:
        """Get completion items at the given position"""
        ...

    async def resolve_completion(
        self, completion_item: types.CompletionItem
    ) -> types.CompletionItem:
        """Resolve the given completion item"""
        ...

    async def get_semantic_tokens(self) -> types.SemanticTokens | None:
        """Get semantic tokens for the current document"""
        ...
