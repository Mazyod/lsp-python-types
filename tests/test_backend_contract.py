"""Backend contract suite — invariants every LSP backend in this package must satisfy.

These tests encode the cross-backend guarantees the package promises consumers,
so a new backend can't silently land with a regression in any of them. New
backends added to this package must pass every test in this file without
per-backend skips. If a real backend can't satisfy an invariant, that's a
package-level bug — fix the normalization layer in `Session`, not the test.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

import lsp_types
from lsp_types.pyrefly.backend import PyreflyBackend
from lsp_types.pyright.backend import PyrightBackend
from lsp_types.ty.backend import TyBackend
from lsp_types.zuban.backend import ZubanBackend


@pytest.fixture(params=[PyrightBackend, PyreflyBackend, TyBackend, ZubanBackend])
def lsp_backend(request):
    return request.param()


async def test_contract_completion_returns_completion_list(lsp_backend, tmp_path: Path):
    """get_completion uniformly returns a CompletionList — never None or a bare list."""
    code = """\
class Widget:
    def describe(self) -> str:
        return "widget"

obj = Widget()
obj.
"""
    session = await lsp_types.Session.create(
        lsp_backend, base_path=tmp_path, initial_code=code
    )
    try:
        completions = await session.get_completion(
            lsp_types.Position(line=5, character=4)
        )
        assert isinstance(completions, dict)
        assert "items" in completions
        assert "isIncomplete" in completions
        assert len(completions["items"]) >= 1
    finally:
        await session.shutdown()


async def test_contract_hover_carries_range(lsp_backend, tmp_path: Path):
    """get_hover_info uniformly surfaces a `range` field — synthesized if omitted."""
    code = """\
def greet(name: str) -> str:
    return f"Hello, {name}"
"""
    session = await lsp_types.Session.create(
        lsp_backend, base_path=tmp_path, initial_code=code
    )
    try:
        hover = await session.get_hover_info(lsp_types.Position(line=0, character=4))
        assert hover is not None
        assert "range" in hover
    finally:
        await session.shutdown()


async def test_contract_diagnostics_on_type_error(lsp_backend, tmp_path: Path):
    """Every backend reports at least one diagnostic on an obvious type error."""
    code = """\
def greet(name: str) -> str:
    return name + 123
"""
    session = await lsp_types.Session.create(
        lsp_backend, base_path=tmp_path, initial_code=code
    )
    try:
        diagnostics = await session.get_diagnostics()
        assert len(diagnostics) >= 1
    finally:
        await session.shutdown()


async def test_contract_no_unhandled_notification_logs(
    lsp_backend, tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    """Session lifecycle must not surface unhandled-notification stderr.

    `LSPProcess._read_stderr` forwards every server stderr line at ERROR level.
    Backends that ignore notifications we send (e.g. ty and Zuban for
    workspace/didChangeConfiguration) surface as "unhandled notification"
    stderr — the package's job is to gate the notification at the source so
    consumers never see this.
    """
    caplog.set_level(logging.ERROR, logger="lsp-types")

    session = await lsp_types.Session.create(
        lsp_backend, base_path=tmp_path, initial_code="x = 1"
    )
    try:
        offenders = [
            record.message
            for record in caplog.records
            if "unhandled" in record.message.lower()
            or "didChangeConfiguration" in record.message
        ]
        assert not offenders, f"unexpected unhandled-notification logs: {offenders}"
    finally:
        await session.shutdown()
