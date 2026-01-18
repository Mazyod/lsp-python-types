import re

from ..lsp_schema import Request
from .generate_methods import method_to_enum_name
from .helpers import StructureKind, format_comment, format_type, indentation

method_to_symbol_name = {
    "codeAction/resolve": "resolve_code_action",
    "codeLens/resolve": "resolve_code_lens",
    "callHierarchy/incomingCalls": "incoming_calls",
    "callHierarchy/outgoingCalls": "outgoing_calls",
    "client/registerCapability": "register_capability",
    "client/unregisterCapability": "unregister_capability",
    "completionItem/resolve": "resolve_completion_item",
    "documentLink/resolve": "resolve_document_link",
    "initialize": "initialize",
    "inlayHint/resolve": "resolve_inlay_hint",
    "shutdown": "shutdown",
    "textDocument/implementation": "implementation",
    "textDocument/typeDefinition": "type_definition",
    "textDocument/documentColor": "document_color",
    "textDocument/colorPresentation": "color_presentation",
    "textDocument/foldingRange": "folding_range",
    "textDocument/declaration": "declaration",
    "textDocument/selectionRange": "selection_range",
    "textDocument/prepareCallHierarchy": "prepare_call_hierarchy",
    "textDocument/semanticTokens/full": "semantic_tokens_full",
    "textDocument/semanticTokens/full/delta": "semantic_tokens_delta",
    "textDocument/semanticTokens/range": "semantic_tokens_range",
    "textDocument/linkedEditingRange": "linked_editing_range",
    "textDocument/moniker": "moniker",
    "textDocument/prepareTypeHierarchy": "prepare_type_hierarchy",
    "textDocument/inlineValue": "inline_value",
    "textDocument/inlayHint": "inlay_hint",
    "textDocument/diagnostic": "text_document_diagnostic",
    "textDocument/willSaveWaitUntil": "will_save_wait_until",
    "textDocument/completion": "completion",
    "textDocument/hover": "hover",
    "textDocument/signatureHelp": "signature_help",
    "textDocument/definition": "definition",
    "textDocument/references": "references",
    "textDocument/documentHighlight": "document_highlight",
    "textDocument/documentSymbol": "document_symbol",
    "textDocument/codeAction": "code_action",
    "textDocument/codeLens": "code_lens",
    "textDocument/documentLink": "document_link",
    "textDocument/formatting": "formatting",
    "textDocument/rangeFormatting": "range_formatting",
    "textDocument/onTypeFormatting": "on_type_formatting",
    "textDocument/rename": "rename",
    "textDocument/prepareRename": "prepare_rename",
    "textDocument/inlineCompletion": "inline_completion",
    "textDocument/rangesFormatting": "ranges_formatting",
    "typeHierarchy/supertypes": "type_hierarchy_supertypes",
    "typeHierarchy/subtypes": "type_hierarchy_subtypes",
    "window/workDoneProgress/create": "create_work_done_progress",
    "window/showDocument": "show_document",
    "window/showMessageRequest": "show_message_request",
    "workspace/applyEdit": "apply_edit",
    "workspace/codeLens/refresh": "code_lens_refresh",
    "workspace/configuration": "workspace_configuration",
    "workspace/diagnostic": "workspace_diagnostic",
    "workspace/diagnostic/refresh": "diagnostic_refresh",
    "workspace/executeCommand": "execute_command",
    "workspace/inlayHint/refresh": "inlay_hint_refresh",
    "workspace/inlineValue/refresh": "inline_value_refresh",
    "workspace/foldingRange/refresh": "folding_range_refresh",
    "workspace/textDocumentContent": "workspace_text_document_content",
    "workspace/textDocumentContent/refresh": "text_document_content_refresh",
    "workspace/willCreateFiles": "will_create_files",
    "workspace/willRenameFiles": "will_rename_files",
    "workspace/willDeleteFiles": "will_delete_files",
    "workspace/workspaceFolders": "workspace_folders",
    "workspace/semanticTokens/refresh": "semantic_tokens_refresh",
    "workspace/symbol": "workspace_symbol",
    "workspaceSymbol/resolve": "resolve_workspace_symbol",
}


def generate_requests(requests: list[Request]) -> list[str]:
    generated_requests = []
    failed = False
    for request in requests:
        if request["messageDirection"] == "serverToClient":
            continue

        try:
            generated_requests.append(generate_request_func(request))
        except Exception as e:
            print(f"Error generating request: {e}")
            failed = True

    if failed:
        raise Exception("Failed to generate requests")

    return generated_requests


def generate_request_func(request: Request) -> str:
    method = request["method"]
    symbol_name = method_to_symbol_name.get(method)
    enum_name = method_to_enum_name(method)

    if not symbol_name:
        raise Exception("Please define a symbol name for ", method)

    params = request.get("params", {})
    formatted_params = ["self"]
    if params:
        if isinstance(params, list):
            raise Exception(
                "You need to add code to handle when params is of type list[_Type]"
            )

        # ... I implemented the case when the params is a referenceS
        # "params": {
        #     "kind": "reference",
        #     "name": "ImplementationParams"
        # },
        params_type = params.get("name")
        if not params_type:
            raise Exception(
                "I expected params to be of type _Type. But got: " + str(params)
            )
        formatted_params += [f"params: types.{params_type}"]

    result_type = format_type(
        request["result"], {"root_symbol_name": ""}, StructureKind.Class
    )
    result_type = prefix_lsp_types(result_type)

    # fix  Expected class type but received "str"
    result_type = result_type.replace("DefinitionLink", "LocationLink")
    result_type = result_type.replace("DeclarationLink", "LocationLink")

    result = f"{indentation}async def {symbol_name}({', '.join(formatted_params)}) -> {result_type}:"

    documentation = format_comment(request.get("documentation"), 2 * indentation)
    if documentation:
        result += f"\n{documentation}"

    result += f"""
{indentation}{indentation}return await self.dispatcher(methods.Request.{enum_name}, {"params" if params else "None"})
"""

    return result


def prefix_lsp_types(text: str) -> str:
    return re.sub(r"'(\w+)'", r"types.\1", text)
