# LSP Types

[![PyPI version](https://img.shields.io/pypi/v/lsp-types.svg?logo=pypi&logoColor=white)](https://pypi.org/project/lsp-types/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Tests](https://github.com/Mazyod/lsp-python-types/actions/workflows/python-tests.yml/badge.svg)](https://github.com/Mazyod/lsp-python-types/actions/workflows/python-tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Typed Python interfaces for the Language Server Protocol, with async sessions
and process pooling for Python language servers. Built on
[Sublime LSP’s generated types](https://github.com/sublimelsp/lsp-python-types).
Python 3.12+; one runtime dependency, `tomlkit`.

## 🧙 Meet your party

<img src="https://raw.githubusercontent.com/Mazyod/lsp-python-types/main/assets/images/lsp-party.png" width="800" alt="Pixel-art party: Pyright the blue sentinel, Pyrefly the coral artificer, ty the green scout, and Zuban the purple diplomat." />

- 🛡️ **[Pyright — the sentinel](https://github.com/Mazyod/lsp-python-types/blob/main/docs/research/landscape.md#pyright--the-sentinel).**
  Broad typing support and configurable execution environments.
  Choose **basedpyright** for extra diagnostics, baselines and semantic highlighting.
- 🔧 **[Pyrefly — the artificer](https://github.com/Mazyod/lsp-python-types/blob/main/docs/research/pyrefly.md).**
  Framework-aware analysis with opt-in regex and `mock.patch` checks.
- 🏹 **[ty — the scout](https://github.com/Mazyod/lsp-python-types/blob/main/docs/research/landscape.md#ty--the-scout).**
  Incremental analysis, explanatory diagnostics and precise type narrowing.
- 🤝 **[Zuban — the diplomat](https://github.com/Mazyod/lsp-python-types/blob/main/docs/research/landscape.md#zuban--the-diplomat).**
  Mypy-compatible configuration and editor inference for untyped code.

## 🚀 Start a session

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

## ✨ Features

All four backends support diagnostics, hover, completion, signature help and rename.

| Feature | Pyright | basedpyright | Pyrefly | ty | Zuban |
|---|---|---|---|---|---|
| Semantic highlighting | ❌ | ✅ | ✅ | ✅ | ✅ |
| Completion documentation via resolve | ✅ | ✅ | ❌ | ❌ | ✅ |

Pyrefly returns completion items unchanged on resolve; ty does not support the
request. ty hover returns the type without the symbol name.

📖 [API & lifecycle](https://github.com/Mazyod/lsp-python-types/blob/main/docs/USAGE.md) ·
🎨 [Semantic tokens](https://github.com/Mazyod/lsp-python-types/blob/main/docs/SEMANTIC_TOKENS.md) ·
🧭 [Backend guide](https://github.com/Mazyod/lsp-python-types/blob/main/docs/research/landscape.md) ·
🎮 [Browser playground](https://mazyod.com/lsp-python-types/)

## 🛠️ Development

```sh
uv sync --all-extras --locked
npm install -g basedpyright
uv run pytest tests
uvx pyright --pythonpath .venv/bin/python
uvx ruff check .
make generate-latest-types
```
