from typing import List
from ..lsp_schema import Notification
from .helpers import format_comment, indentation


method_to_symbol_name = {
    "workspace/didChangeWorkspaceFolders": "did_change_workspace_folders",
    "window/workDoneProgress/cancel": "cancel_work_done_progress",
    "workspace/didCreateFiles": "did_create_files",
    "workspace/didRenameFiles": "did_rename_files",
    "workspace/didDeleteFiles": "did_delete_files",
    "notebookDocument/didOpen": "did_open_notebook_document",
    "notebookDocument/didChange": "did_change_notebook_document",
    "notebookDocument/didSave": "did_save_notebook_document",
    "notebookDocument/didClose": "did_close_notebook_document",
    "initialized": "initialized",
    "exit": "exit",
    "workspace/didChangeConfiguration": "workspace_did_change_configuration",
    "textDocument/didOpen": "did_open_text_document",
    "textDocument/didChange": "did_change_text_document",
    "textDocument/didClose": "did_close_text_document",
    "textDocument/didSave": "did_save_text_document",
    "textDocument/willSave": "will_save_text_document",
    "workspace/didChangeWatchedFiles": "did_change_watched_files",
    "$/setTrace": "set_trace",
    "$/cancelRequest": "cancel_request",
    "$/progress": "progress",
}


def generate_notifications(notifications: List[Notification]) -> List[str]:
    def toString(notification: Notification) -> str:
        return generate_notification(notification)

    return [
        toString(notification)
        for notification in notifications
        if notification["messageDirection"] in ["clientToServer", "both"]
    ]


def generate_notification(notification: Notification) -> str:
    result = ""
    method = notification["method"]
    symbol_name = method_to_symbol_name.get(method)
    if not symbol_name:
        raise Exception("Please define a symbol name for ", method)
    params = notification.get("params", {})
    formatted_params = ""
    if params:
        if isinstance(params, list):
            raise Exception(
                "You need to add code to handle when params is of type List[_Type]"
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
        formatted_params = f",  params: types.{params_type}"
    result += f"{indentation}def {symbol_name}(self{formatted_params}) -> None:"
    documentation = format_comment(
        notification.get("documentation"), indentation + indentation
    )
    if documentation.strip():
        result += f"\n{documentation}"
    result += f"""\n{indentation}{indentation}return self.dispatcher("{method}"{", params" if params else ""})\n"""

    return result
