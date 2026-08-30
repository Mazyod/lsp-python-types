"""Shared fixtures for the backend-parametrized test suite."""

from __future__ import annotations

import pytest

from lsp_types.pyrefly.backend import PyreflyBackend
from lsp_types.pyright.backend import PyrightBackend
from lsp_types.session import LSPBackend
from lsp_types.ty.backend import TyBackend
from lsp_types.zuban.backend import ZubanBackend

# Explicit ids keep `-k "not Pyright"` reliable across every module that uses
# the fixture, rather than depending on the class name pytest infers.
BACKENDS = [
    pytest.param(PyrightBackend, id="Pyright"),
    pytest.param(PyreflyBackend, id="Pyrefly"),
    pytest.param(TyBackend, id="ty"),
    pytest.param(ZubanBackend, id="Zuban"),
]


@pytest.fixture(params=BACKENDS)
def lsp_backend(request: pytest.FixtureRequest) -> LSPBackend:
    """Parametrized fixture providing Pyright, Pyrefly, ty, and Zuban backends."""
    return request.param()


@pytest.fixture
def backend_name(lsp_backend: LSPBackend) -> str:
    """Helper fixture to get the backend name for test identification."""
    return lsp_backend.__class__.__name__.replace("Backend", "").lower()
