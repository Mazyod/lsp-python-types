# LSP Types
_Publish the excellent work of [Sublime LSP](https://github.com/sublimelsp/lsp-python-types) as a PyPI package._

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

Using an LSP session through stdio:

```python
from lsp_types.session import LSPSession, ProcessLaunchInfo

process_info = ProcessLaunchInfo(cmd=[
    "pyright-langserver", "--stdio"
])

async with LSPSession(process_info) as session:
    # Initialize the session
    ...

    # Grab a typed listener
    diagnostics_listener = session.notify.on_publish_diagnostics(timeout=1.0)

    # Send a notification
    await session.notify.did_open_text_document(...)

    # Wait for diagnostics to come in
    diagnostics = await diagnostics_listener
```

## Development

- Requires Python 3.11+.
- Requires `poetry` for dev dependencies.

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
