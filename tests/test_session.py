import os

import lsp_types as types
from lsp_types.process import LSPProcess, ProcessLaunchInfo


async def test_server_initialize():
    # Create an LSP Process with pyright-langserver
    # * Note: pyright must be installed and accessible (e.g. npm i -g pyright)
    process_info = ProcessLaunchInfo(cmd=["pyright-langserver", "--stdio"])
    async with LSPProcess(process_info) as process:
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

        result = await process.send.initialize(initialize_params)

        # Basic assertions about the response
        assert result is not None
        # assert "serverInfo" in result
        # assert result["serverInfo"]["name"] == "jedi-language-server"

        assert "hoverProvider" in result["capabilities"]
        # assert result["capabilities"]["hoverProvider"] is True
        assert result["capabilities"]["hoverProvider"] == {"workDoneProgress": True}

        # Update settings via didChangeConfiguration
        await process.notify.workspace_did_change_configuration({"settings": {}})

        # Prepare a diagnostics listener ahead of time
        diagnostics_listener = process.notify.on_publish_diagnostics(timeout=1.0)

        # Simulate opening a document via didOpen
        document_uri = "file:///test.py"  # Test file path
        document_version = 1
        document_text = "print('Correct code')"  # Simple test content

        await process.notify.did_open_text_document(
            {
                "textDocument": {
                    "uri": document_uri,
                    "languageId": types.LanguageKind.Python,
                    "version": document_version,
                    "text": document_text,
                }
            }
        )

        diagnostics = await diagnostics_listener
        assert diagnostics["diagnostics"] == []

        # Simulate changing the document via didChange

        document_text += "\nprint('New line')"
        document_version += 1

        await process.notify.did_change_text_document(
            {
                "textDocument": {
                    "uri": document_uri,
                    "version": document_version,
                },
                "contentChanges": [{"text": document_text}],
            }
        )
