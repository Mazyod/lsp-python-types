from ..lsp_schema import Notification
from .helpers import format_comment, indentation

method_to_symbol_name = {
    "exit": "exit",
    "initialized": "initialized",
    "notebookDocument/didChange": "did_change_notebook_document",
    "notebookDocument/didClose": "did_close_notebook_document",
    "notebookDocument/didOpen": "did_open_notebook_document",
    "notebookDocument/didSave": "did_save_notebook_document",
    "telemetry/event": "telemetry_event",
    "textDocument/didChange": "did_change_text_document",
    "textDocument/didClose": "did_close_text_document",
    "textDocument/didOpen": "did_open_text_document",
    "textDocument/didSave": "did_save_text_document",
    "textDocument/publishDiagnostics": "publish_diagnostics",
    "textDocument/willSave": "will_save_text_document",
    "window/logMessage": "log_message",
    "window/showMessage": "show_message",
    "window/workDoneProgress/cancel": "cancel_work_done_progress",
    "workspace/didChangeConfiguration": "workspace_did_change_configuration",
    "workspace/didChangeWatchedFiles": "did_change_watched_files",
    "workspace/didChangeWorkspaceFolders": "did_change_workspace_folders",
    "workspace/didCreateFiles": "did_create_files",
    "workspace/didDeleteFiles": "did_delete_files",
    "workspace/didRenameFiles": "did_rename_files",
    "$/cancelRequest": "cancel_request",
    "$/logTrace": "log_trace",
    "$/progress": "progress",
    "$/setTrace": "set_trace",
}


def generate_notifications(notifications: list[Notification]) -> list[str]:
    generated_notifications = []
    failed = False
    for notification in notifications:
        method = notification["method"]
        symbol_name = method_to_symbol_name.get(method)

        if not symbol_name:
            print(f"Please define a symbol name for: {method = }")
            failed = True
            continue

        messageDirection = notification["messageDirection"]
        if messageDirection == "both" or messageDirection == "serverToClient":
            handler = generate_notification_handler(method, symbol_name, notification)
            generated_notifications.append(handler)
        if messageDirection == "both" or messageDirection == "clientToServer":
            func = generate_notification_func(method, symbol_name, notification)
            generated_notifications.append(func)

    if failed:
        raise Exception("Failed to generate notifications")

    return generated_notifications


def generate_notification_handler(
    method: str, symbol_name: str, notification: Notification
) -> str:
    params = notification.get("params", {})
    formatted_params = ["self", "*", "timeout: float | None = None"]
    return_type = "None"
    if params:
        if isinstance(params, list):
            raise NotImplementedError("Params of type list is not implemented")

        params_type = params.get("name")
        if not params_type:
            raise Exception(f"Expected params to have 'name', but got: {params!r}")
        return_type = f"types.{params_type}"

    return_type = f"asyncio.Future[{return_type}]"
    result = f"{indentation}def on_{symbol_name}({', '.join(formatted_params)}) -> {return_type}:"

    documentation = format_comment(notification.get("documentation"), 2 * indentation)
    if documentation.strip():
        result += f"\n{documentation}"

    result += f"""\n{indentation}{indentation}return self.on_notification("{method}", timeout)\n"""

    return result


def generate_notification_func(
    method: str, symbol_name: str, notification: Notification
) -> str:
    params = notification.get("params", {})
    formatted_params = ["self"]
    if params:
        if isinstance(params, list):
            raise NotImplementedError("Params of type list is not implemented")

        # ... I implemented the case when the params is a referenceS
        # "params": {
        #     "kind": "reference",
        #     "name": "ImplementationParams"
        # },
        params_type = params.get("name")
        if not params_type:
            raise Exception(f"Expected params to have 'name', but got: {params!r}")
        formatted_params += [f"params: types.{params_type}"]

    result = f"{indentation}def {symbol_name}({', '.join(formatted_params)}):"

    documentation = format_comment(notification.get("documentation"), 2 * indentation)
    if documentation.strip():
        result += f"\n{documentation}"

    result += f"""\n{indentation}{indentation}return self.dispatcher("{method}", {"params" if params else "None"})\n"""

    return result
