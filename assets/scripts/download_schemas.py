import asyncio
from pathlib import Path

import httpx


lsp_schema_url = "https://raw.githubusercontent.com/microsoft/vscode-languageserver-node/main/protocol/metaModel.schema.json"
meta_model_url = "https://raw.githubusercontent.com/microsoft/vscode-languageserver-node/main/protocol/metaModel.json"
pyright_schema_url = "https://raw.githubusercontent.com/microsoft/pyright/main/packages/vscode-pyright/schemas/pyrightconfig.schema.json"


async def main():
    base_path = Path("./assets")
    async with httpx.AsyncClient() as client:
        downloads = [
            (lsp_schema_url, base_path / "lsprotocol/lsp.schema.json"),
            (meta_model_url, base_path / "lsprotocol/lsp.json"),
            (pyright_schema_url, base_path / "lsps/pyright.schema.json"),
        ]

        contents = await asyncio.gather(*[client.get(url) for url, _ in downloads])

        for (_, dest), content in zip(downloads, contents):
            dest.write_text(content.text)


if __name__ == "__main__":
    asyncio.run(main())
