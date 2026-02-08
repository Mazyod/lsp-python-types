# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "lsp-types>=0.12.3",
# ]
# ///
"""
Extract semantic token legends from all LSP backends.

This script initializes each backend and captures the SemanticTokensLegend
from the server's capabilities. The output can be used to update the
docs/SEMANTIC_TOKENS.md documentation.

Run with:
    uv run python examples/extract_semantic_legends.py
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from lsp_types import types
from lsp_types.process import LSPProcess
from lsp_types.pyrefly.backend import PyreflyBackend
from lsp_types.pyright.backend import PyrightBackend
from lsp_types.ty.backend import TyBackend

# Suppress LSP server stderr output (info/warning messages)
logging.getLogger("lsp-types").setLevel(logging.CRITICAL)


async def extract_legend(
    backend_name: str,
    process_info,
    capabilities: types.ClientCapabilities,
    base_path: Path,
) -> dict | None:
    """Initialize a backend and extract its semantic tokens legend."""
    process = LSPProcess(process_info)
    try:
        await process.start()

        # Initialize and capture the result with timeout
        init_result = await asyncio.wait_for(
            process.send.initialize(
                {
                    "processId": None,
                    "rootUri": f"file://{base_path}",
                    "rootPath": str(base_path),
                    "capabilities": capabilities,
                }
            ),
            timeout=10.0,
        )

        # Send initialized notification (required by LSP spec)
        await process.notify.initialized({})

        # Extract server version info
        server_info = init_result.get("serverInfo", {})
        server_version = server_info.get("version", "unknown")

        # Extract semantic tokens provider from server capabilities
        server_caps = init_result.get("capabilities", {})
        semantic_provider = server_caps.get("semanticTokensProvider")

        if semantic_provider is None:
            # Try requesting tokens anyway - some servers respond without advertising
            await process.notify.did_open_text_document(
                {
                    "textDocument": {
                        "uri": f"file://{base_path}/test.py",
                        "languageId": types.LanguageKind.Python,
                        "version": 1,
                        "text": "x = 1\n",
                    }
                }
            )
            tokens = await asyncio.wait_for(
                process.send.semantic_tokens_full(
                    {"textDocument": {"uri": f"file://{base_path}/test.py"}}
                ),
                timeout=5.0,
            )
            if tokens and tokens.get("data"):
                print(
                    f"  {backend_name}: No legend advertised, but returns tokens (unusable without legend)"
                )
            else:
                print(f"  {backend_name}: No semantic tokens provider")
            print(f"  {backend_name}: version {server_version}")
            return None

        legend = semantic_provider.get("legend")
        if legend is None:
            print(f"  {backend_name}: No legend in semantic tokens provider")
            return None

        return {
            "backend": backend_name,
            "version": server_version,
            "tokenTypes": legend.get("tokenTypes", []),
            "tokenModifiers": legend.get("tokenModifiers", []),
        }
    except asyncio.TimeoutError:
        print(f"  {backend_name}: Timeout during initialization")
        return None
    except Exception as e:
        print(f"  {backend_name}: Error - {type(e).__name__}: {e}")
        return None
    finally:
        await process.stop()


def print_legend_table(legend: dict) -> None:
    """Print a legend as markdown tables."""
    backend = legend["backend"]
    version = legend["version"]
    token_types = legend["tokenTypes"]
    token_modifiers = legend["tokenModifiers"]

    print(f"\n### {backend}\n")
    print(f"> Version: {version}\n")

    # Token Types table
    print("#### Token Types\n")
    print("| Index | Token Type |")
    print("|------:|------------|")
    for idx, token_type in enumerate(token_types):
        print(f"| {idx} | `{token_type}` |")

    # Token Modifiers table
    print("\n#### Token Modifiers\n")
    print("| Bit | Modifier |")
    print("|----:|----------|")
    for idx, modifier in enumerate(token_modifiers):
        print(f"| {idx} | `{modifier}` |")


async def main() -> None:
    print("# Semantic Token Legends by Backend\n")
    print("Extracting legends from all backends...\n")

    with TemporaryDirectory(prefix="lsp-legend-") as tmp:
        base_path = Path(tmp)

        # Create a minimal file for ty (which requires files on disk)
        (base_path / "new.py").write_text("# placeholder\n")

        backends = [
            ("Pyright (basedpyright)", PyrightBackend()),
            ("Pyrefly", PyreflyBackend()),
            ("ty", TyBackend()),
        ]

        legends = []
        for name, backend in backends:
            print(f"Initializing {name}...")
            backend.write_config(base_path, {})
            process_info = backend.create_process_launch_info(base_path, {})
            capabilities = backend.get_lsp_capabilities()

            legend = await extract_legend(name, process_info, capabilities, base_path)
            if legend:
                legends.append(legend)
                print(
                    f"  {name}: version {legend['version']}, {len(legend['tokenTypes'])} types, {len(legend['tokenModifiers'])} modifiers"
                )

        print("\n" + "=" * 60)
        print("MARKDOWN OUTPUT FOR docs/SEMANTIC_TOKENS.md")
        print("=" * 60)

        for legend in legends:
            print_legend_table(legend)


if __name__ == "__main__":
    asyncio.run(main())
