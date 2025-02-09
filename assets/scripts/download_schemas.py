from pathlib import Path
from urllib.request import urlopen


schema_url = "https://raw.githubusercontent.com/microsoft/vscode-languageserver-node/main/protocol/metaModel.schema.json"
meta_model_url = "https://raw.githubusercontent.com/microsoft/vscode-languageserver-node/main/protocol/metaModel.json"


if __name__ == "__main__":
    lsp_json_schema = urlopen(schema_url).read().decode("utf-8")
    Path("./assets/lsprotocol/lsp.schema.json").write_text(lsp_json_schema)

    lsp_meta_model = urlopen(meta_model_url).read().decode("utf-8")
    Path("./assets/lsprotocol/lsp.json").write_text(lsp_meta_model)
