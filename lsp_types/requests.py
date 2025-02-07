# FIXME: Figure out how this was generated, or generate using TypeScript Compiler
# Code generated. DO NOT EDIT.
# LSP v3.17.0

"""
This file provides the python interface corresponding to the requests and notifications defined in Typescript in the language server protocol.
This file is obtained from https://github.com/predragnikolic/OLSP under the MIT License with the following terms:

MIT License

Copyright (c) 2023 Предраг Николић

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from typing import List, Mapping, Protocol, Union, Any

from . import types


__all__ = [
    "RequestDispatcher",
    "NotificationDispatcher",
    "Request",
    "Notification",
]


class RequestDispatcher(Protocol):
    async def send_request(self, method: str, params: Mapping | None = None) -> Any: ...


class NotificationDispatcher(Protocol):
    def send_notification(self, method: str, params: Mapping | None = None) -> None: ...


class Request:
    def __init__(self, dispatcher: RequestDispatcher):
        self.dispatcher = dispatcher

    async def implementation(
        self, params: types.ImplementationParams
    ) -> Union["types.Definition", List["types.LocationLink"], None]:
        """A request to resolve the implementation locations of a symbol at a given text
        document position. The request's parameter is of type [TextDocumentPositionParams]
        (#TextDocumentPositionParams) the response is of type {@link Definition} or a
        Thenable that resolves to such."""
        return await self.dispatcher.send_request("textDocument/implementation", params)

    async def type_definition(
        self, params: types.TypeDefinitionParams
    ) -> Union["types.Definition", List["types.LocationLink"], None]:
        """A request to resolve the type definition locations of a symbol at a given text
        document position. The request's parameter is of type [TextDocumentPositionParams]
        (#TextDocumentPositionParams) the response is of type {@link Definition} or a
        Thenable that resolves to such."""
        return await self.dispatcher.send_request("textDocument/typeDefinition", params)

    async def document_color(
        self, params: types.DocumentColorParams
    ) -> List["types.ColorInformation"]:
        """A request to list all color symbols found in a given text document. The request's
        parameter is of type {@link DocumentColorParams} the
        response is of type {@link ColorInformation ColorInformation[]} or a Thenable
        that resolves to such."""
        return await self.dispatcher.send_request("textDocument/documentColor", params)

    async def color_presentation(
        self, params: types.ColorPresentationParams
    ) -> List["types.ColorPresentation"]:
        """A request to list all presentation for a color. The request's
        parameter is of type {@link ColorPresentationParams} the
        response is of type {@link ColorInformation ColorInformation[]} or a Thenable
        that resolves to such."""
        return await self.dispatcher.send_request(
            "textDocument/colorPresentation", params
        )

    async def folding_range(
        self, params: types.FoldingRangeParams
    ) -> Union[List["types.FoldingRange"], None]:
        """A request to provide folding ranges in a document. The request's
        parameter is of type {@link FoldingRangeParams}, the
        response is of type {@link FoldingRangeList} or a Thenable
        that resolves to such."""
        return await self.dispatcher.send_request("textDocument/foldingRange", params)

    async def declaration(
        self, params: types.DeclarationParams
    ) -> Union["types.Declaration", List["types.LocationLink"], None]:
        """A request to resolve the type definition locations of a symbol at a given text
        document position. The request's parameter is of type [TextDocumentPositionParams]
        (#TextDocumentPositionParams) the response is of type {@link Declaration}
        or a typed array of {@link DeclarationLink} or a Thenable that resolves
        to such."""
        return await self.dispatcher.send_request("textDocument/declaration", params)

    async def selection_range(
        self, params: types.SelectionRangeParams
    ) -> Union[List["types.SelectionRange"], None]:
        """A request to provide selection ranges in a document. The request's
        parameter is of type {@link SelectionRangeParams}, the
        response is of type {@link SelectionRange SelectionRange[]} or a Thenable
        that resolves to such."""
        return await self.dispatcher.send_request("textDocument/selectionRange", params)

    async def prepare_call_hierarchy(
        self, params: types.CallHierarchyPrepareParams
    ) -> Union[List["types.CallHierarchyItem"], None]:
        """A request to result a `CallHierarchyItem` in a document at a given position.
        Can be used as an input to an incoming or outgoing call hierarchy.

        @since 3.16.0"""
        return await self.dispatcher.send_request(
            "textDocument/prepareCallHierarchy", params
        )

    async def incoming_calls(
        self, params: types.CallHierarchyIncomingCallsParams
    ) -> Union[List["types.CallHierarchyIncomingCall"], None]:
        """A request to resolve the incoming calls for a given `CallHierarchyItem`.

        @since 3.16.0"""
        return await self.dispatcher.send_request("callHierarchy/incomingCalls", params)

    async def outgoing_calls(
        self, params: types.CallHierarchyOutgoingCallsParams
    ) -> Union[List["types.CallHierarchyOutgoingCall"], None]:
        """A request to resolve the outgoing calls for a given `CallHierarchyItem`.

        @since 3.16.0"""
        return await self.dispatcher.send_request("callHierarchy/outgoingCalls", params)

    async def semantic_tokens_full(
        self, params: types.SemanticTokensParams
    ) -> Union["types.SemanticTokens", None]:
        """@since 3.16.0"""
        return await self.dispatcher.send_request(
            "textDocument/semanticTokens/full", params
        )

    async def semantic_tokens_delta(
        self, params: types.SemanticTokensDeltaParams
    ) -> Union["types.SemanticTokens", "types.SemanticTokensDelta", None]:
        """@since 3.16.0"""
        return await self.dispatcher.send_request(
            "textDocument/semanticTokens/full/delta", params
        )

    async def semantic_tokens_range(
        self, params: types.SemanticTokensRangeParams
    ) -> Union["types.SemanticTokens", None]:
        """@since 3.16.0"""
        return await self.dispatcher.send_request(
            "textDocument/semanticTokens/range", params
        )

    async def linked_editing_range(
        self, params: types.LinkedEditingRangeParams
    ) -> Union["types.LinkedEditingRanges", None]:
        """A request to provide ranges that can be edited together.

        @since 3.16.0"""
        return await self.dispatcher.send_request(
            "textDocument/linkedEditingRange", params
        )

    async def will_create_files(
        self, params: types.CreateFilesParams
    ) -> Union["types.WorkspaceEdit", None]:
        """The will create files request is sent from the client to the server before files are actually
        created as long as the creation is triggered from within the client.

        @since 3.16.0"""
        return await self.dispatcher.send_request("workspace/willCreateFiles", params)

    async def will_rename_files(
        self, params: types.RenameFilesParams
    ) -> Union["types.WorkspaceEdit", None]:
        """The will rename files request is sent from the client to the server before files are actually
        renamed as long as the rename is triggered from within the client.

        @since 3.16.0"""
        return await self.dispatcher.send_request("workspace/willRenameFiles", params)

    async def will_delete_files(
        self, params: types.DeleteFilesParams
    ) -> Union["types.WorkspaceEdit", None]:
        """The did delete files notification is sent from the client to the server when
        files were deleted from within the client.

        @since 3.16.0"""
        return await self.dispatcher.send_request("workspace/willDeleteFiles", params)

    async def moniker(
        self, params: types.MonikerParams
    ) -> Union[List["types.Moniker"], None]:
        """A request to get the moniker of a symbol at a given text document position.
        The request parameter is of type {@link TextDocumentPositionParams}.
        The response is of type {@link Moniker Moniker[]} or `null`."""
        return await self.dispatcher.send_request("textDocument/moniker", params)

    async def prepare_type_hierarchy(
        self, params: types.TypeHierarchyPrepareParams
    ) -> Union[List["types.TypeHierarchyItem"], None]:
        """A request to result a `TypeHierarchyItem` in a document at a given position.
        Can be used as an input to a subtypes or supertypes type hierarchy.

        @since 3.17.0"""
        return await self.dispatcher.send_request(
            "textDocument/prepareTypeHierarchy", params
        )

    async def type_hierarchy_supertypes(
        self, params: types.TypeHierarchySupertypesParams
    ) -> Union[List["types.TypeHierarchyItem"], None]:
        """A request to resolve the supertypes for a given `TypeHierarchyItem`.

        @since 3.17.0"""
        return await self.dispatcher.send_request("typeHierarchy/supertypes", params)

    async def type_hierarchy_subtypes(
        self, params: types.TypeHierarchySubtypesParams
    ) -> Union[List["types.TypeHierarchyItem"], None]:
        """A request to resolve the subtypes for a given `TypeHierarchyItem`.

        @since 3.17.0"""
        return await self.dispatcher.send_request("typeHierarchy/subtypes", params)

    async def inline_value(
        self, params: types.InlineValueParams
    ) -> Union[List["types.InlineValue"], None]:
        """A request to provide inline values in a document. The request's parameter is of
        type {@link InlineValueParams}, the response is of type
        {@link InlineValue InlineValue[]} or a Thenable that resolves to such.

        @since 3.17.0"""
        return await self.dispatcher.send_request("textDocument/inlineValue", params)

    async def inlay_hint(
        self, params: types.InlayHintParams
    ) -> Union[List["types.InlayHint"], None]:
        """A request to provide inlay hints in a document. The request's parameter is of
        type {@link InlayHintsParams}, the response is of type
        {@link InlayHint InlayHint[]} or a Thenable that resolves to such.

        @since 3.17.0"""
        return await self.dispatcher.send_request("textDocument/inlayHint", params)

    async def resolve_inlay_hint(self, params: types.InlayHint) -> "types.InlayHint":
        """A request to resolve additional properties for an inlay hint.
        The request's parameter is of type {@link InlayHint}, the response is
        of type {@link InlayHint} or a Thenable that resolves to such.

        @since 3.17.0"""
        return await self.dispatcher.send_request("inlayHint/resolve", params)

    async def text_document_diagnostic(
        self, params: types.DocumentDiagnosticParams
    ) -> "types.DocumentDiagnosticReport":
        """The document diagnostic request definition.

        @since 3.17.0"""
        return await self.dispatcher.send_request("textDocument/diagnostic", params)

    async def workspace_diagnostic(
        self, params: types.WorkspaceDiagnosticParams
    ) -> "types.WorkspaceDiagnosticReport":
        """The workspace diagnostic request definition.

        @since 3.17.0"""
        return await self.dispatcher.send_request("workspace/diagnostic", params)

    async def initialize(
        self, params: types.InitializeParams
    ) -> "types.InitializeResult":
        """The initialize request is sent from the client to the server.
        It is sent once as the request after starting up the server.
        The requests parameter is of type {@link InitializeParams}
        the response if of type {@link InitializeResult} of a Thenable that
        resolves to such."""
        return await self.dispatcher.send_request("initialize", params)

    async def shutdown(self) -> None:
        """A shutdown request is sent from the client to the server.
        It is sent once when the client decides to shutdown the
        server. The only notification that is sent after a shutdown request
        is the exit event."""
        return await self.dispatcher.send_request("shutdown")

    async def will_save_wait_until(
        self, params: types.WillSaveTextDocumentParams
    ) -> Union[List["types.TextEdit"], None]:
        """A document will save request is sent from the client to the server before
        the document is actually saved. The request can return an array of TextEdits
        which will be applied to the text document before it is saved. Please note that
        clients might drop results if computing the text edits took too long or if a
        server constantly fails on this request. This is done to keep the save fast and
        reliable."""
        return await self.dispatcher.send_request(
            "textDocument/willSaveWaitUntil", params
        )

    async def completion(
        self, params: types.CompletionParams
    ) -> Union[List["types.CompletionItem"], "types.CompletionList", None]:
        """Request to request completion at a given text document position. The request's
        parameter is of type {@link TextDocumentPosition} the response
        is of type {@link CompletionItem CompletionItem[]} or {@link CompletionList}
        or a Thenable that resolves to such.

        The request can delay the computation of the {@link CompletionItem.detail `detail`}
        and {@link CompletionItem.documentation `documentation`} properties to the `completionItem/resolve`
        request. However, properties that are needed for the initial sorting and filtering, like `sortText`,
        `filterText`, `insertText`, and `textEdit`, must not be changed during resolve.
        """
        return await self.dispatcher.send_request("textDocument/completion", params)

    async def resolve_completion_item(
        self, params: types.CompletionItem
    ) -> "types.CompletionItem":
        """Request to resolve additional information for a given completion item.The request's
        parameter is of type {@link CompletionItem} the response
        is of type {@link CompletionItem} or a Thenable that resolves to such."""
        return await self.dispatcher.send_request("completionItem/resolve", params)

    async def hover(self, params: types.HoverParams) -> Union["types.Hover", None]:
        """Request to request hover information at a given text document position. The request's
        parameter is of type {@link TextDocumentPosition} the response is of
        type {@link Hover} or a Thenable that resolves to such."""
        return await self.dispatcher.send_request("textDocument/hover", params)

    async def signature_help(
        self, params: types.SignatureHelpParams
    ) -> Union["types.SignatureHelp", None]:
        return await self.dispatcher.send_request("textDocument/signatureHelp", params)

    async def definition(
        self, params: types.DefinitionParams
    ) -> Union["types.Definition", List["types.LocationLink"], None]:
        """A request to resolve the definition location of a symbol at a given text
        document position. The request's parameter is of type [TextDocumentPosition]
        (#TextDocumentPosition) the response is of either type {@link Definition}
        or a typed array of {@link DefinitionLink} or a Thenable that resolves
        to such."""
        return await self.dispatcher.send_request("textDocument/definition", params)

    async def references(
        self, params: types.ReferenceParams
    ) -> Union[List["types.Location"], None]:
        """A request to resolve project-wide references for the symbol denoted
        by the given text document position. The request's parameter is of
        type {@link ReferenceParams} the response is of type
        {@link Location Location[]} or a Thenable that resolves to such."""
        return await self.dispatcher.send_request("textDocument/references", params)

    async def document_highlight(
        self, params: types.DocumentHighlightParams
    ) -> Union[List["types.DocumentHighlight"], None]:
        """Request to resolve a {@link DocumentHighlight} for a given
        text document position. The request's parameter is of type [TextDocumentPosition]
        (#TextDocumentPosition) the request response is of type [DocumentHighlight[]]
        (#DocumentHighlight) or a Thenable that resolves to such."""
        return await self.dispatcher.send_request(
            "textDocument/documentHighlight", params
        )

    async def document_symbol(
        self, params: types.DocumentSymbolParams
    ) -> Union[List["types.SymbolInformation"], List["types.DocumentSymbol"], None]:
        """A request to list all symbols found in a given text document. The request's
        parameter is of type {@link TextDocumentIdentifier} the
        response is of type {@link SymbolInformation SymbolInformation[]} or a Thenable
        that resolves to such."""
        return await self.dispatcher.send_request("textDocument/documentSymbol", params)

    async def code_action(
        self, params: types.CodeActionParams
    ) -> Union[List[Union["types.Command", "types.CodeAction"]], None]:
        """A request to provide commands for the given text document and range."""
        return await self.dispatcher.send_request("textDocument/codeAction", params)

    async def resolve_code_action(self, params: types.CodeAction) -> "types.CodeAction":
        """Request to resolve additional information for a given code action.The request's
        parameter is of type {@link CodeAction} the response
        is of type {@link CodeAction} or a Thenable that resolves to such."""
        return await self.dispatcher.send_request("codeAction/resolve", params)

    async def workspace_symbol(
        self, params: types.WorkspaceSymbolParams
    ) -> Union[List["types.SymbolInformation"], List["types.WorkspaceSymbol"], None]:
        """A request to list project-wide symbols matching the query string given
        by the {@link WorkspaceSymbolParams}. The response is
        of type {@link SymbolInformation SymbolInformation[]} or a Thenable that
        resolves to such.

        @since 3.17.0 - support for WorkspaceSymbol in the returned data. Clients
         need to advertise support for WorkspaceSymbols via the client capability
         `workspace.symbol.resolveSupport`.
        """
        return await self.dispatcher.send_request("workspace/symbol", params)

    async def resolve_workspace_symbol(
        self, params: types.WorkspaceSymbol
    ) -> "types.WorkspaceSymbol":
        """A request to resolve the range inside the workspace
        symbol's location.

        @since 3.17.0"""
        return await self.dispatcher.send_request("workspaceSymbol/resolve", params)

    async def code_lens(
        self, params: types.CodeLensParams
    ) -> Union[List["types.CodeLens"], None]:
        """A request to provide code lens for the given text document."""
        return await self.dispatcher.send_request("textDocument/codeLens", params)

    async def resolve_code_lens(self, params: types.CodeLens) -> "types.CodeLens":
        """A request to resolve a command for a given code lens."""
        return await self.dispatcher.send_request("codeLens/resolve", params)

    async def document_link(
        self, params: types.DocumentLinkParams
    ) -> Union[List["types.DocumentLink"], None]:
        """A request to provide document links"""
        return await self.dispatcher.send_request("textDocument/documentLink", params)

    async def resolve_document_link(
        self, params: types.DocumentLink
    ) -> "types.DocumentLink":
        """Request to resolve additional information for a given document link. The request's
        parameter is of type {@link DocumentLink} the response
        is of type {@link DocumentLink} or a Thenable that resolves to such."""
        return await self.dispatcher.send_request("documentLink/resolve", params)

    async def formatting(
        self, params: types.DocumentFormattingParams
    ) -> Union[List["types.TextEdit"], None]:
        """A request to to format a whole document."""
        return await self.dispatcher.send_request("textDocument/formatting", params)

    async def range_formatting(
        self, params: types.DocumentRangeFormattingParams
    ) -> Union[List["types.TextEdit"], None]:
        """A request to to format a range in a document."""
        return await self.dispatcher.send_request(
            "textDocument/rangeFormatting", params
        )

    async def on_type_formatting(
        self, params: types.DocumentOnTypeFormattingParams
    ) -> Union[List["types.TextEdit"], None]:
        """A request to format a document on type."""
        return await self.dispatcher.send_request(
            "textDocument/onTypeFormatting", params
        )

    async def rename(
        self, params: types.RenameParams
    ) -> Union["types.WorkspaceEdit", None]:
        """A request to rename a symbol."""
        return await self.dispatcher.send_request("textDocument/rename", params)

    async def prepare_rename(
        self, params: types.PrepareRenameParams
    ) -> Union["types.PrepareRenameResult", None]:
        """A request to test and perform the setup necessary for a rename.

        @since 3.16 - support for default behavior"""
        return await self.dispatcher.send_request("textDocument/prepareRename", params)

    async def execute_command(
        self, params: types.ExecuteCommandParams
    ) -> Union["types.LSPAny", None]:
        """A request send from the client to the server to execute a command. The request might return
        a workspace edit which the client will apply to the workspace."""
        return await self.dispatcher.send_request("workspace/executeCommand", params)


class Notification:
    def __init__(self, dispatcher: NotificationDispatcher):
        self.dispatcher = dispatcher

    def did_change_workspace_folders(
        self, params: types.DidChangeWorkspaceFoldersParams
    ) -> None:
        """The `workspace/didChangeWorkspaceFolders` notification is sent from the client to the server when the workspace
        folder configuration changes."""
        return self.dispatcher.send_notification(
            "workspace/didChangeWorkspaceFolders", params
        )

    def cancel_work_done_progress(
        self, params: types.WorkDoneProgressCancelParams
    ) -> None:
        """The `window/workDoneProgress/cancel` notification is sent from  the client to the server to cancel a progress
        initiated on the server side."""
        return self.dispatcher.send_notification(
            "window/workDoneProgress/cancel", params
        )

    def did_create_files(self, params: types.CreateFilesParams) -> None:
        """The did create files notification is sent from the client to the server when
        files were created from within the client.

        @since 3.16.0"""
        return self.dispatcher.send_notification("workspace/didCreateFiles", params)

    def did_rename_files(self, params: types.RenameFilesParams) -> None:
        """The did rename files notification is sent from the client to the server when
        files were renamed from within the client.

        @since 3.16.0"""
        return self.dispatcher.send_notification("workspace/didRenameFiles", params)

    def did_delete_files(self, params: types.DeleteFilesParams) -> None:
        """The will delete files request is sent from the client to the server before files are actually
        deleted as long as the deletion is triggered from within the client.

        @since 3.16.0"""
        return self.dispatcher.send_notification("workspace/didDeleteFiles", params)

    def did_open_notebook_document(
        self, params: types.DidOpenNotebookDocumentParams
    ) -> None:
        """A notification sent when a notebook opens.

        @since 3.17.0"""
        return self.dispatcher.send_notification("notebookDocument/didOpen", params)

    def did_change_notebook_document(
        self, params: types.DidChangeNotebookDocumentParams
    ) -> None:
        return self.dispatcher.send_notification("notebookDocument/didChange", params)

    def did_save_notebook_document(
        self, params: types.DidSaveNotebookDocumentParams
    ) -> None:
        """A notification sent when a notebook document is saved.

        @since 3.17.0"""
        return self.dispatcher.send_notification("notebookDocument/didSave", params)

    def did_close_notebook_document(
        self, params: types.DidCloseNotebookDocumentParams
    ) -> None:
        """A notification sent when a notebook closes.

        @since 3.17.0"""
        return self.dispatcher.send_notification("notebookDocument/didClose", params)

    def initialized(self, params: types.InitializedParams) -> None:
        """The initialized notification is sent from the client to the
        server after the client is fully initialized and the server
        is allowed to send requests from the server to the client."""
        return self.dispatcher.send_notification("initialized", params)

    def exit(self) -> None:
        """The exit event is sent from the client to the server to
        ask the server to exit its process."""
        return self.dispatcher.send_notification("exit")

    def workspace_did_change_configuration(
        self, params: types.DidChangeConfigurationParams
    ) -> None:
        """The configuration change notification is sent from the client to the server
        when the client's configuration has changed. The notification contains
        the changed configuration as defined by the language client."""
        return self.dispatcher.send_notification(
            "workspace/didChangeConfiguration", params
        )

    def did_open_text_document(self, params: types.DidOpenTextDocumentParams) -> None:
        """The document open notification is sent from the client to the server to signal
        newly opened text documents. The document's truth is now managed by the client
        and the server must not try to read the document's truth using the document's
        uri. Open in this sense means it is managed by the client. It doesn't necessarily
        mean that its content is presented in an editor. An open notification must not
        be sent more than once without a corresponding close notification send before.
        This means open and close notification must be balanced and the max open count
        is one."""
        return self.dispatcher.send_notification("textDocument/didOpen", params)

    def did_change_text_document(
        self, params: types.DidChangeTextDocumentParams
    ) -> None:
        """The document change notification is sent from the client to the server to signal
        changes to a text document."""
        return self.dispatcher.send_notification("textDocument/didChange", params)

    def did_close_text_document(self, params: types.DidCloseTextDocumentParams) -> None:
        """The document close notification is sent from the client to the server when
        the document got closed in the client. The document's truth now exists where
        the document's uri points to (e.g. if the document's uri is a file uri the
        truth now exists on disk). As with the open notification the close notification
        is about managing the document's content. Receiving a close notification
        doesn't mean that the document was open in an editor before. A close
        notification requires a previous open notification to be sent."""
        return self.dispatcher.send_notification("textDocument/didClose", params)

    def did_save_text_document(self, params: types.DidSaveTextDocumentParams) -> None:
        """The document save notification is sent from the client to the server when
        the document got saved in the client."""
        return self.dispatcher.send_notification("textDocument/didSave", params)

    def will_save_text_document(self, params: types.WillSaveTextDocumentParams) -> None:
        """A document will save notification is sent from the client to the server before
        the document is actually saved."""
        return self.dispatcher.send_notification("textDocument/willSave", params)

    def did_change_watched_files(
        self, params: types.DidChangeWatchedFilesParams
    ) -> None:
        """The watched files notification is sent from the client to the server when
        the client detects changes to file watched by the language client."""
        return self.dispatcher.send_notification(
            "workspace/didChangeWatchedFiles", params
        )

    def set_trace(self, params: types.SetTraceParams) -> None:
        return self.dispatcher.send_notification("$/setTrace", params)

    def cancel_request(self, params: types.CancelParams) -> None:
        return self.dispatcher.send_notification("$/cancelRequest", params)

    def progress(self, params: types.ProgressParams) -> None:
        return self.dispatcher.send_notification("$/progress", params)
