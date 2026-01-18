# LSP Types

[![PyPI version](https://img.shields.io/pypi/v/lsp-types.svg?logo=pypi&logoColor=white)](https://pypi.org/project/lsp-types/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Tests](https://github.com/Mazyod/lsp-python-types/actions/workflows/python-tests.yml/badge.svg)](https://github.com/Mazyod/lsp-python-types/actions/workflows/python-tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

_Publish the excellent work of [Sublime LSP](https://github.com/sublimelsp/lsp-python-types) as a PyPI package._

![image](https://github.com/user-attachments/assets/12b6016a-8e62-4058-8c74-26fcdee1122a)


__LSP Types__ is a Python package that aims to provide a fully typed interface to Language Server Protocol (LSP) interactions. It can be used to simply utilize the types, or to interact with an LSP server over stdio.

The library has minimal dependencies (`tomli-w` for TOML config serialization).

## Installation

```sh
pip install lsp-types
```

## Usage

Using the LSP types:

```python
import lsp_types

# Use the types
```

Using an LSP process through stdio:

> [!TIP]
> Recommend using [basedpyright](https://github.com/DetachHead/basedpyright) for extended features.

```python
from lsp_types.process import LSPProcess, ProcessLaunchInfo

process_info = ProcessLaunchInfo(cmd=[
    "pyright-langserver", "--stdio"
])

async with LSPProcess(process_info) as process:
    # Initialize the process
    ...

    # Grab a typed listener
    diagnostics_listener = process.notify.on_publish_diagnostics(timeout=1.0)

    # Send a notification (`await` is optional. It ensures messages have been drained)
    await process.notify.did_open_text_document(...)

    # Wait for diagnostics to come in
    diagnostics = await diagnostics_listener
```

## LSPs

The following LSPs are available out of the box:

- [Pyright](https://github.com/microsoft/pyright)
- [Pyrefly](https://github.com/facebook/pyrefly)
- [ty](https://github.com/astral-sh/ty) - Astral's fast Python type checker

## Feature Support Matrix

### Legend

| Symbol | Meaning |
|--------|---------|
| :white_check_mark: | Fully supported |
| :warning: | Partial support (see notes) |
| :x: | Not supported |
| :grey_question: | Not tested / Not exposed in API |

### Features by Backend

> Last verified: basedpyright 1.36.2, Pyrefly 0.48.2, ty 0.0.12

| Feature | Pyright | Pyrefly | ty | Notes |
|---------|:-------:|:-------:|:--:|-------|
| Diagnostics | :white_check_mark: | :white_check_mark: | :warning: | ty requires files on disk |
| Hover | :white_check_mark: | :white_check_mark: | :white_check_mark: | ty shows type only, not variable name |
| Completion | :white_check_mark: | :white_check_mark: | :warning: | ty requires files on disk |
| Completion Resolution | :white_check_mark: | :x: | :white_check_mark: | Pyrefly: not yet supported |
| Signature Help | :white_check_mark: | :white_check_mark: | :white_check_mark: | |
| Rename | :white_check_mark: | :warning: | :warning: | Pyrefly: disabled for external files; ty: requires files on disk |
| Semantic Tokens | :white_check_mark:\* | :white_check_mark:\*\* | :white_check_mark: | \*basedpyright recommended; \*\*Pyrefly: legend not advertised (see docs) |
| Go to Definition | :grey_question: | :grey_question: | :grey_question: | Not exposed in Session API |
| Find References | :grey_question: | :grey_question: | :grey_question: | Not exposed in Session API |
| Code Actions | :grey_question: | :grey_question: | :grey_question: | Not exposed in Session API |
| Formatting | :grey_question: | :grey_question: | :grey_question: | Not exposed in Session API |

> See [Feature Verification Guide](docs/FEATURE_VERIFICATION.md) for methodology on maintaining this table.

For detailed documentation:
- [Semantic Tokens Reference](docs/SEMANTIC_TOKENS.md) - Token types and modifiers for Monaco/editor integration
- [Pyrefly Known Limitations](lsp_types/pyrefly/KNOWN_LIMITATIONS.md)
- [ty Known Limitations](lsp_types/ty/KNOWN_LIMITATIONS.md)

### Pyright Example

```python
from lsp_types import Session
from lsp_types.pyright.backend import PyrightBackend

async def test_pyright_session():
    code = """\
def greet(name: str) -> str:
    return 123
"""

    session = await Session.create(PyrightBackend(), initial_code=code)
    diagnostics = await session.get_diagnostics()

    assert diagnostics != []

    code = """\
def greet(name: str) -> str:
    return f"Hello, {name}"
"""

    await session.update_code(code)
    diagnostics = await session.get_diagnostics()
    assert diagnostics == []

    await session.shutdown()
```

## Development

- Requires Python 3.12+.
- Requires `uv` for dev dependencies.

Generate latest types in one go:
```sh
make generate-latest-types
```

Download the latest json schema:
```sh
make download-schemas
```

Generate the types:
```sh
make generate-types
```

Copy the `lsp_types/types.py` file to your project.

NOTE: Do not import types that begin with `__`. These types are internal types and are not meant to be used.

### TODOs

- Support server request handlers.
