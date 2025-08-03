# LSP Types

[![PyPI version](https://badge.fury.io/py/lsp-types.svg)](https://badge.fury.io/py/lsp-types)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://github.com/Mazyod/lsp-python-types/actions/workflows/python-tests.yml/badge.svg)](https://github.com/Mazyod/lsp-python-types/actions/workflows/python-tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

_Publish the excellent work of [Sublime LSP](https://github.com/sublimelsp/lsp-python-types) as a PyPI package._

![image](https://github.com/user-attachments/assets/12b6016a-8e62-4058-8c74-26fcdee1122a)


__LSP Types__ is a Python package that aims to provide a fully typed interface to Language Server Protocol (LSP) interactions. It can be used to simply utilize the types, or to interact with an LSP server over stdio.

It is a goal to maintain zero-dependency status for as long as possible.

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

### Pyright

```python
async def test_pyright_session():
    code = """\
def greet(name: str) -> str:
    return 123
"""

    pyright_session = await Session.create(PyrightBackend(), initial_code=code)
    diagnostics = await pyright_session.get_diagnostics()

    assert diagnostics != []

    code = """\
def greet(name: str) -> str:
    return f"Hello, {name}"
"""

    assert await pyright_session.update_code(code) == 2

    diagnostics = await pyright_session.get_diagnostics()
    assert diagnostics == []
```

## Development

- Requires Python 3.11+.
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
make generate-schemas
```

Copy the `lsp_types/types.py` file to your project.

NOTE: Do not import types that begin with `__`. These types are internal types and are not meant to be used.

### TODOs

- Automate package releases on Github.
- Support server request handlers.
