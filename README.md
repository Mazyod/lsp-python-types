# Setup

Requires Python 3.11+.

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
