import asyncio
import os
import datetime as dt

import lsp_types as types
from lsp_types.session import LSPSession, ProcessLaunchInfo


async def test_server_initialize():
    # Create an LSP Session with pyright-langserver
    # * Note: pyright must be installed and accessible (e.g. npm i -g pyright)
    process_info = ProcessLaunchInfo(cmd=["pyright-langserver", "--stdio"])
    async with LSPSession(process_info) as session:

        async def wait_for_notification(
            method: str, *, timeout: dt.timedelta = dt.timedelta(seconds=1)
        ):
            async def _notifications_iter():
                async for notification in session.notifications():
                    if notification["method"] == method:
                        return notification
                assert False, f"Notification {method} not received"

            return await asyncio.wait_for(
                _notifications_iter(), timeout.total_seconds()
            )

        # Send initialize request
        initialize_params: types.InitializeParams = {
            # NOTE: If processId is set to `1` or something, the server will crash after ~3 seconds
            "processId": None,
            "rootUri": f"file://{os.getcwd()}",
            "rootPath": os.getcwd(),
            "capabilities": {
                "textDocument": {
                    "publishDiagnostics": {
                        "versionSupport": True,
                        "tagSupport": {
                            "valueSet": [
                                types.DiagnosticTag.Unnecessary,
                                types.DiagnosticTag.Deprecated,
                            ]
                        },
                    },
                    "hover": {
                        "contentFormat": [
                            types.MarkupKind.Markdown,
                            types.MarkupKind.PlainText,
                        ],
                    },
                    "signatureHelp": {},
                }
            },
        }

        result = await session.send.initialize(initialize_params)

        # Basic assertions about the response
        assert result is not None
        # assert "serverInfo" in result
        # assert result["serverInfo"]["name"] == "jedi-language-server"

        assert "hoverProvider" in result["capabilities"]
        # assert result["capabilities"]["hoverProvider"] is True
        assert result["capabilities"]["hoverProvider"] == {"workDoneProgress": True}

        # Update settings via didChangeConfiguration
        await session.notify.workspace_did_change_configuration({"settings": {}})

        # Simulate opening a document via didOpen
        document_uri = "file:///test.py"  # Test file path
        document_version = 1
        document_text = "print('Correct code')"  # Simple test content

        await session.notify.did_open_text_document(
            {
                "textDocument": {
                    "uri": document_uri,
                    "languageId": types.LanguageKind.Python,
                    "version": document_version,
                    "text": document_text,
                }
            }
        )

        diagnostics = await wait_for_notification("textDocument/publishDiagnostics")
        assert diagnostics["params"]["diagnostics"] == []

        # Simulate changing the document via didChange

        document_text += "\nprint('New line')"
        document_version += 1

        await session.notify.did_change_text_document(
            {
                "textDocument": {
                    "uri": document_uri,
                    "version": document_version,
                },
                "contentChanges": [{"text": document_text}],
            }
        )
