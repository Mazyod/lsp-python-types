# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "lsp-types>=0.12.2",
#     "rich>=14.2.0",
# ]
# ///
"""
Minimal hover-only repro for cross-package circular types between external
packages pkgb and pkgc added via search_path/extraPaths.

Layout (both pkgb and pkgc live outside the workspace root and are added via
search paths):
- pkgb/b.py: defines PkgB and holds a PkgC instance
- pkgc/c.py: defines PkgC and holds a PkgB instance

The active document instantiates PkgB and PkgC, binds a few variables, and logs
hover contents to check whether types flow across the boundary.

This script runs for both Pyrefly and Pyright backends automatically.

Run with:
    uv run python examples/pyrefly_circular_imports.py
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent

from rich.console import Console
from rich.markdown import Markdown

import lsp_types
from lsp_types.pyrefly.backend import PyreflyBackend
from lsp_types.pyright.backend import PyrightBackend

console = Console()


# Simple structured logging helpers
def log_step(title: str) -> None:
    console.print(f"\n=== {title} ===")


def log_result(label: str, value) -> None:
    if label.endswith(".md"):
        console.print(f"{label}:\n")
        console.print(Markdown(value))
    else:
        console.print(f"{label}: {value}")


PKGB_B = dedent(
    """\
    from __future__ import annotations

    from pkgc.c import PkgC

    class PkgB:
        def __init__(self) -> None:
            self.c: PkgC = PkgC(self)

    """
)

PKGC_C = dedent(
    """\
    from __future__ import annotations

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from pkgb.b import PkgB


    class PkgC:
        def __init__(self, b: PkgB) -> None:
            self.b: PkgB = b

    """
)

ACTIVE_CODE = dedent(
    """\
    from pkgb.b import PkgB
    from pkgc.c import PkgC

    b = PkgB()
    c = PkgC(b)

    c_from_b = b.c
    b_from_c = c.b
    """
)


def prepare_workspace(pkgb_dir: Path, pkgc_dir: Path) -> None:
    """Create pkgb and pkgc packages in external paths used via search_path/extraPaths."""
    pkgb = pkgb_dir / "pkgb"
    pkgc = pkgc_dir / "pkgc"

    pkgb.mkdir(parents=True, exist_ok=True)
    pkgc.mkdir(parents=True, exist_ok=True)

    pkgb.joinpath("__init__.py").write_text("")
    pkgc.joinpath("__init__.py").write_text("")
    pkgb.joinpath("b.py").write_text(PKGB_B)
    pkgc.joinpath("c.py").write_text(PKGC_C)


async def run_backend(
    backend_name: str,
    backend,
    options_key: str,
    root: Path,
    external_pkgb: Path,
    external_pkgc: Path,
) -> None:
    """Run the circular imports test for a specific backend."""
    console.rule(
        f"[bold cyan]{backend_name.upper()} Backend[/bold cyan]", characters="="
    )

    session = await lsp_types.Session.create(
        backend,
        base_path=root,
        initial_code=ACTIVE_CODE,
        options={options_key: [str(external_pkgb), str(external_pkgc)]},
    )

    try:
        log_step("Diagnostics for active document")
        diagnostics = await session.get_diagnostics()
        log_result("Diagnostics count", len(diagnostics))
        if diagnostics:
            log_result("Diagnostics", diagnostics)

        hover_targets = {
            "b (PkgB)": lsp_types.Position(line=3, character=0),
            "c (PkgC)": lsp_types.Position(line=4, character=0),
            "c_from_b (PkgC)": lsp_types.Position(line=6, character=0),
            "b_from_c (PkgB)": lsp_types.Position(line=7, character=0),
        }

        for label, position in hover_targets.items():
            log_step(f"Hover: {label}")
            hover = await session.get_hover_info(position)
            if hover:
                match hover["contents"]:
                    case {"kind": "markdown", "value": value}:
                        log_result("Hover contents.md", value)
                    case contents:
                        log_result("Hover contents", contents)
    finally:
        await session.shutdown()


async def main() -> None:
    with (
        TemporaryDirectory(prefix="circular-root-") as tmp_root,
        TemporaryDirectory(prefix="circular-pkgb-") as tmp_pkgb,
        TemporaryDirectory(prefix="circular-pkgc-") as tmp_pkgc,
    ):
        root = Path(tmp_root)
        external_pkgb = Path(tmp_pkgb)
        external_pkgc = Path(tmp_pkgc)
        prepare_workspace(external_pkgb, external_pkgc)

        console.print()
        console.print("[bold]Circular Imports Test - Running for both backends[/bold]")
        console.print()

        # Run Pyrefly backend
        await run_backend(
            "pyrefly",
            PyreflyBackend(),
            "search_path",
            root,
            external_pkgb,
            external_pkgc,
        )

        console.print("\n")

        # Run Pyright backend
        await run_backend(
            "pyright",
            PyrightBackend(),
            "extraPaths",
            root,
            external_pkgb,
            external_pkgc,
        )


if __name__ == "__main__":
    asyncio.run(main())
