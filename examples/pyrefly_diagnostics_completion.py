# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "lsp-types[pyrefly]>=0.12.3",
#     "rich>=14.2.0",
# ]
# ///
"""
 Small end-to-end script that exercises LSP backends for diagnostics and
 completion. It spins up a throwaway workspace containing a single module, opens an
 in-memory document, walks through multiple code mutations (4 diagnostic steps, 2
 completion steps, followed by a stress loop), and ensures the final version is clean.
 Rich console output is used to highlight each step.

This script runs for both Pyrefly and Pyright backends automatically.

Run with:
    uv run python examples/pyrefly_diagnostics_completion.py
"""

from __future__ import annotations

import asyncio
import logging
import textwrap
import time
import typing as t
from pathlib import Path
from tempfile import TemporaryDirectory

from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

import lsp_types
from lsp_types.pyrefly.backend import PyreflyBackend
from lsp_types.pyright.backend import PyrightBackend

console = Console()
STRESS_ITERATIONS = 30


def user_print(message: str) -> None:
    """Print user-facing messages with a leading blank line for clarity."""
    console.print()
    console.print()
    console.print(message)


class IDEController:
    """Minimal pager-like interface that appends code and proxies LSP queries."""

    def __init__(self, session: lsp_types.Session) -> None:
        self.session = session
        self.code = ""
        self.cursor_index = 0
        self.timings: list[tuple[str, float]] = []

    @classmethod
    async def create(
        cls, backend, workspace: Path, *, label: str = "Session initialization"
    ) -> "IDEController":
        start = time.perf_counter()
        session = await lsp_types.Session.create(
            backend, base_path=workspace, initial_code=""
        )
        controller = cls(session)
        controller._record(label, start)
        return controller

    def _record(self, label: str, start: float) -> None:
        elapsed = time.perf_counter() - start
        self.timings.append((label, elapsed))

    def _cursor_position(self) -> lsp_types.Position:
        if not self.code:
            return lsp_types.Position(line=0, character=0)
        lines = self.code.splitlines()
        return lsp_types.Position(line=len(lines) - 1, character=len(lines[-1]))

    def _find_marker(self, marker: str, *, after: bool = False) -> lsp_types.Position:
        lines = self.code.splitlines()
        for idx, line in enumerate(lines):
            col = line.find(marker)
            if col != -1:
                if after:
                    col += len(marker)
                return lsp_types.Position(line=idx, character=col)
        raise ValueError(f"Marker '{marker}' not found in code")

    async def write_code(self, snippet: str, *, label: str) -> int:
        self.code += snippet
        self.cursor_index = len(self.code)
        start = time.perf_counter()
        version = await self.session.update_code(self.code)
        self._record(label, start)
        return version

    async def diagnostics(self, *, label: str) -> t.Any:
        start = time.perf_counter()
        result = await self.session.get_diagnostics()
        self._record(label, start)
        return result

    async def hover(self, marker: str, *, label: str) -> t.Any:
        position = self._find_marker(marker)
        start = time.perf_counter()
        hover_info = await self.session.get_hover_info(position)
        self._record(label, start)
        return hover_info

    async def semantic_tokens(self, *, label: str) -> t.Any:
        start = time.perf_counter()
        tokens = await self.session.get_semantic_tokens()
        self._record(label, start)
        return tokens

    async def completion(self, *, label: str) -> t.Any:
        position = self._cursor_position()
        start = time.perf_counter()
        completions = await self.session.get_completion(position)
        self._record(label, start)
        return completions

    async def shutdown(self, *, label: str = "Session shutdown") -> None:
        start = time.perf_counter()
        await self.session.shutdown()
        self._record(label, start)


def prepare_workspace(root: Path) -> None:
    """Create a minimal module the active document can import from."""
    module_dir = root / "supportlib"
    module_dir.mkdir(parents=True, exist_ok=True)

    module_dir.joinpath("__init__.py").write_text("")
    module_dir.joinpath("models.py").write_text(
        textwrap.dedent(
            """\
            from __future__ import annotations


            class Widget:
                def __init__(self, name: str) -> None:
                    self.name = name

                def describe(self) -> str:
                    return f"Widget<{self.name}>"


            def build_widget(name: str) -> Widget:
                return Widget(name)
            """
        )
    )


def render_diagnostics(diagnostics) -> None:
    if not diagnostics:
        user_print("[green]No diagnostics reported.[/]")
        return

    table = Table(title="Diagnostics", show_edge=False, header_style="bold cyan")
    table.add_column("Severity")
    table.add_column("Message")
    table.add_column("Range")

    severity_map = {1: "Error", 2: "Warning", 3: "Information", 4: "Hint"}

    for diag in diagnostics:
        severity = severity_map.get(diag.get("severity"), "Unknown")
        message = diag.get("message", "").strip()
        rng = diag.get("range", {})
        start = rng.get("start", {})
        end = rng.get("end", {})
        loc = f"{start.get('line')}:{start.get('character')} -> {end.get('line')}:{end.get('character')}"
        table.add_row(severity, message, loc)

    console.print()
    console.print()
    console.print(table)


async def run_backend(backend_name: str, backend, workspace: Path) -> None:
    """Run the diagnostics and completion test for a specific backend."""
    console.rule(
        f"[bold cyan]{backend_name.upper()} Diagnostics + Completion[/bold cyan]",
        characters="=",
    )

    controller = await IDEController.create(backend, workspace)
    user_print(f"[dim]Session initialized in {controller.timings[-1][1]:.3f}s[/dim]")

    initial_snippet = textwrap.dedent(
        """\
        from supportlib.models import build_widget


        def compile_report(raw_name: str) -> str:
            widget = build_widget(raw_name)
            return format_helper(widget)
        """
    )

    mid_snippet = textwrap.dedent(
        """\


        def format_helper(widget):
            highlight = rich_format(widget)
            return highlight.upper()
        """
    )

    final_snippet = textwrap.dedent(
        """\


        def rich_format(widget):
            return widget.describe()


        current = build_widget("preview")
        final_preview = compile_report("preview")
        """
    )

    try:
        user_print("[bold]Step 1:[/] Diagnostics on intentionally incomplete code")
        version_initial = await controller.write_code(
            initial_snippet, label="Initial code write"
        )
        user_print(f"Document version is now {version_initial}")

        diagnostics = await controller.diagnostics(label="Initial diagnostics")
        render_diagnostics(diagnostics)

        user_print("[bold]Step 1.1:[/] Hover on compile_report in initial code")
        hover_initial = await controller.hover("compile_report", label="Initial hover")
        user_print(f"Hover (initial) received: {hover_initial is not None}")

        user_print("[bold]Step 1.2:[/] Semantic tokens snapshot (initial code)")
        tokens_initial = await controller.semantic_tokens(
            label="Initial semantic tokens"
        )
        token_count_initial = (
            len(tokens_initial.get("data", [])) if tokens_initial else 0
        )
        user_print(f"Semantic tokens (initial) count: {token_count_initial}")

        user_print(
            "[bold]Step 2:[/] Append helper (still faulty) and re-run diagnostics"
        )
        version_mid = await controller.write_code(
            mid_snippet, label="Helper definition write"
        )
        user_print(f"Document version is now {version_mid}")

        diagnostics_mid = await controller.diagnostics(label="Mid diagnostics")
        render_diagnostics(diagnostics_mid)

        user_print("[bold]Step 2.1:[/] Hover on format_helper in mid code")
        hover_mid = await controller.hover("format_helper", label="Mid hover")
        user_print(f"Hover (mid) received: {hover_mid is not None}")

        user_print("[bold]Step 2.2:[/] Semantic tokens snapshot (mid code)")
        tokens_mid = await controller.semantic_tokens(label="Mid semantic tokens")
        token_count_mid = len(tokens_mid.get("data", [])) if tokens_mid else 0
        user_print(f"Semantic tokens (mid) count: {token_count_mid}")

        user_print("[bold]Step 3:[/] Finalize code and confirm clean diagnostics")
        version_final = await controller.write_code(
            final_snippet, label="Rich formatter write"
        )
        user_print(f"Document version is now {version_final}")

        diagnostics_final = await controller.diagnostics(label="Final diagnostics")
        render_diagnostics(diagnostics_final)

        user_print("[bold]Step 4:[/] Completion request at cursor")
        await controller.write_code(
            "\ncompletion_preview = current.",
            label="Completion anchor write",
        )
        completions = await controller.completion(label="Completion request 1")

        if completions is None:
            user_print("[yellow]No completion items returned[/]")
        else:
            items = (
                completions.get("items", [])
                if isinstance(completions, dict)
                else completions
            )
            top_labels = [item.get("label") for item in items[:5]]
            user_print(
                f"Received {len(items)} completion items; top labels: {top_labels}"
            )

        user_print("[bold]Step 5:[/] Second completion request (same cursor)")
        completions_second = await controller.completion(label="Completion request 2")
        if completions_second is None:
            user_print("[yellow]No completion items returned[/]")
        else:
            items = (
                completions_second.get("items", [])
                if isinstance(completions_second, dict)
                else completions_second
            )
            top_labels = [item.get("label") for item in items[:3]]
            user_print(f"Completion count: {len(items)}; sample labels: {top_labels}")

        user_print("[bold]Step 6:[/] Finish completion snippet and verify diagnostics")
        await controller.write_code(
            "describe()\n",
            label="Complete completion snippet",
        )
        diagnostics_post = await controller.diagnostics(
            label="Post completion diagnostics"
        )
        render_diagnostics(diagnostics_post)

        user_print(
            f"[bold]Step 7:[/] Stress test loop ({STRESS_ITERATIONS} iterations)"
        )
        for idx in range(STRESS_ITERATIONS):
            loop_id = idx + 1
            user_print(f"[bold]- Iteration {loop_id}[/] Append helper and query LSP")

            stress_snippet = textwrap.dedent(
                f"""


                def stress_helper_{idx}(seed: str) -> str:
                    probe = compile_report(seed)
                    return probe.upper()
                """
            )
            version_stress = await controller.write_code(
                stress_snippet, label=f"Stress helper write {loop_id}"
            )
            user_print(f"Document version is now {version_stress}")

            diagnostics_loop = await controller.diagnostics(
                label=f"Stress diagnostics {loop_id}"
            )
            render_diagnostics(diagnostics_loop)

            hover_loop = await controller.hover(
                f"stress_helper_{idx}", label=f"Stress hover {loop_id}"
            )
            user_print(f"Hover (stress {loop_id}) received: {hover_loop is not None}")

            tokens_loop = await controller.semantic_tokens(
                label=f"Stress semantic tokens {loop_id}"
            )
            token_count_loop = len(tokens_loop.get("data", [])) if tokens_loop else 0
            user_print(f"Semantic tokens (stress {loop_id}) count: {token_count_loop}")

            await controller.write_code(
                f"\nstress_completion_{idx} = current.",
                label=f"Stress completion anchor {loop_id}",
            )
            completions_loop = await controller.completion(
                label=f"Stress completion {loop_id}"
            )
            if completions_loop is None:
                user_print("[yellow]No completion items returned[/]")
            else:
                items = (
                    completions_loop.get("items", [])
                    if isinstance(completions_loop, dict)
                    else completions_loop
                )
                top_labels = [item.get("label") for item in items[:3]]
                user_print(
                    f"Stress completion {loop_id}: {len(items)} items, sample {top_labels}"
                )

            await controller.write_code(
                "describe()\n",
                label=f"Stress completion finish {loop_id}",
            )

            diagnostics_finalize = await controller.diagnostics(
                label=f"Stress diagnostics confirm {loop_id}"
            )
            render_diagnostics(diagnostics_finalize)

    finally:
        await controller.shutdown()
        user_print(f"[dim]Session shutdown in {controller.timings[-1][1]:.3f}s[/dim]")

    console.print()
    console.print()
    console.rule(f"[bold cyan]Timing Summary - {backend_name.upper()}[/bold cyan]")

    table = Table(title="Operation Timings", show_edge=False, header_style="bold cyan")
    table.add_column("Operation", style="white")
    table.add_column("Time (s)", justify="right", style="green")

    total_time = 0.0
    for label, elapsed in controller.timings:
        table.add_row(label, f"{elapsed:.3f}")
        total_time += elapsed

    table.add_row("─" * 30, "─" * 10, style="dim")
    table.add_row("[bold]Total", f"[bold]{total_time:.3f}")

    console.print()
    console.print(table)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                show_path=False,
                show_time=False,
                show_level=False,
            )
        ],
    )

    with TemporaryDirectory(prefix="lsp-example-", delete=False) as tmp:
        workspace = Path(tmp)
        prepare_workspace(workspace)
        user_print(f"Workspace prepared at [bold]{workspace}[/]")
        console.print()

        # Run Pyrefly backend
        await run_backend("pyrefly", PyreflyBackend(), workspace)

        console.print("\n\n")

        # Run Pyright backend
        await run_backend("pyright", PyrightBackend(node_flags=["--prof"]), workspace)

        console.print("\n\n")

        # Print workspace location
        user_print(f"Workspace location: [bold]{workspace}[/]")


if __name__ == "__main__":
    asyncio.run(main())
