# LSP Types

[![PyPI version](https://img.shields.io/pypi/v/lsp-types.svg?logo=pypi&logoColor=white)](https://pypi.org/project/lsp-types/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Tests](https://github.com/Mazyod/lsp-python-types/actions/workflows/python-tests.yml/badge.svg)](https://github.com/Mazyod/lsp-python-types/actions/workflows/python-tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Typed Python interfaces for the Language Server Protocol, with async sessions
and process pooling for Python language servers. Built on
[Sublime LSP’s generated types](https://github.com/sublimelsp/lsp-python-types).
Python 3.12+; one runtime dependency, `tomlkit`.

## Meet your party

<img src="assets/images/lsp-party.png" width="800" alt="Pixel-art party: Pyright the blue sentinel, Pyrefly the coral artificer, ty the green scout, and Zuban the purple diplomat." />

- **[Pyright — the sentinel](docs/research/landscape.md#pyright--the-veteran).**
  Broad typing support and configurable execution environments. Equip the
  **basedpyright** fork for extra diagnostics, baselines and semantic highlighting;
  those extras are not part of Microsoft Pyright.
- **[Pyrefly — the artificer](docs/research/pyrefly.md).**
  A growing toolbelt: configurable regex and `mock.patch` checks, framework knowledge,
  and experimental tensor/DataFrame analysis. Some tools need explicit settings;
  experimental APIs can change.
- **[ty — the scout](docs/research/landscape.md#ty--the-swift-scout).**
  Built for quick incremental feedback, explanatory diagnostics and precise type
  narrowing. In this adapter, hover favors the type alone and completion resolution
  is unavailable.
- **[Zuban — the diplomat](docs/research/landscape.md#zuban--the-bridge-builder).**
  Bridges Mypy workflows and editor inference for untyped code. Compatibility modes
  are its specialty; value-constrained generic bodies and unused ignores remain
  checking blind spots.

These are personalities, not speed rankings. The linked field notes separate
upstream features from what this library actually tests.

## Start a session

```sh
pip install "lsp-types[pyrefly]"  # Or [ty] / [zuban]
```

```python
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from lsp_types import Session
from lsp_types.pyrefly.backend import PyreflyBackend

async def main():
    with TemporaryDirectory() as workspace:
        session = await Session.create(
            PyreflyBackend(),
            base_path=Path(workspace),
            initial_code='answer: int = "oops"',
        )
        try:
            print(await session.get_diagnostics())
            await session.update_code("answer: int = 42")
            print(await session.get_diagnostics())  # []
        finally:
            await session.shutdown()

asyncio.run(main())
```

Swap in `TyBackend`, `ZubanBackend`, or `PyrightBackend`. For Pyright, install
Node.js and `npm install -g pyright` (or `basedpyright`) separately.
Sessions write backend configuration into `base_path`; use a dedicated workspace
as above. For types alone, `import lsp_types`; no server is needed.

## What works here

Diagnostics, hover, completion, signature help and rename pass across all four
backends. Semantic tokens work with **basedpyright**, Pyrefly, ty and Zuban;
Microsoft Pyright does not provide them. Completion resolution enriches results
with Pyright/basedpyright and Zuban; Pyrefly echoes the item, while ty rejects it.

Verified **2026-09-11**: Pyright **1.1.414**, basedpyright **1.40.1**,
Pyrefly **1.3.0**, ty **0.0.80**, Zuban **0.9.3**.

[Feature evidence & maintenance runbook](docs/FEATURE_VERIFICATION.md) ·
[Semantic tokens](docs/SEMANTIC_TOKENS.md) ·
[Low-level API & lifecycle](docs/USAGE.md) ·
[Maintenance results](docs/MAINTENANCE_2026-09-11.md)

## Development

```sh
uv sync --all-extras --locked
npm install -g basedpyright
uv run pytest
uvx pyright --pythonpath .venv/bin/python
uvx ruff check .
make generate-latest-types
```

The [runbook](docs/FEATURE_VERIFICATION.md) covers testing Microsoft Pyright
separately, regenerating schemas and updating the browser playground.
