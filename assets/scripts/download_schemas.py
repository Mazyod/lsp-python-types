from urllib.request import urlopen

lsp_json_schema = urlopen("https://raw.githubusercontent.com/microsoft/vscode-languageserver-node/main/protocol/metaModel.schema.json").read().decode('utf-8')
open("./assets/lsprotocol/lsp.schema.json", "w").write(lsp_json_schema)

lsp_meta_model = urlopen("https://raw.githubusercontent.com/microsoft/vscode-languageserver-node/main/protocol/metaModel.json").read().decode('utf-8')
open("./assets/lsprotocol/lsp.json", "w").write(lsp_meta_model)
