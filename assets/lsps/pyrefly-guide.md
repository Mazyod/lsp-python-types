# Pyrefly integration reference

Verified with **Pyrefly 1.3.0 on 2026-09-11**. The backend's typed configuration
is maintained in `lsp_types/pyrefly/config_schema.py`; this document is a short
reference, not a generated or exhaustive upstream schema.

## Configuration

Pyrefly reads `pyrefly.toml` or `[tool.pyrefly]` in `pyproject.toml`.
`PyreflyBackend` writes `pyrefly.toml`, converting top-level Python snake_case
keys to TOML kebab-case. Error-code keys inside `errors` should already use
their upstream spelling. For example:

```python
from lsp_types import Session
from lsp_types.pyrefly.backend import PyreflyBackend
from lsp_types.pyrefly.config_schema import Model

options: Model = {
    "preset": "strict",
    "python_version": "3.13",
    "search_path": ["src"],
    "check_unannotated_defs": True,
    "infer_return_types": "checked",
    "errors": {"regex": "error", "missing-attribute-patch-target": "warn"},
}
# In an async function:
# session = await Session.create(PyreflyBackend(), options=options)
```

Errors accept severity strings (`error`, `warn`, `info`, `ignore`) and legacy
booleans. `untyped_def_behavior` remains accepted but is deprecated upstream;
use `check_unannotated_defs` and `infer_return_types` for new configurations.
Plain dictionaries passed to `Session.create(options=...)` can carry options
not yet represented in `Model`.

An unconfigured CLI project may use the minimal `basic` preset or migrate
nearby mypy/Pyright configuration in memory. Explicit configuration makes
comparisons reproducible. `Session.create()` writes a configuration file,
including an empty file when given no options, so its behavior need not match
an unconfigured CLI invocation. See the
[configuration reference](https://pyrefly.org/en/docs/configuration/) and
[1.3.0 configuration implementation](https://github.com/facebook/pyrefly/blob/1.3.0/crates/pyrefly_config/src/base.rs).

## LSP and CLI

The library starts `pyrefly lsp` and communicates over JSON-RPC stdio.
The backend forwards `verbose`, `threads`, and `indexing_mode` as launch flags.
Indexing modes are `none`, `lazy-non-blocking-background` (default), and
`lazy-blocking` (useful for deterministic testing). Disabling indexing limits
features such as references. Pyrefly supports virtual documents opened with
`textDocument/didOpen`; files need not already exist on disk.

The standalone CLI also offers configuration migration (`init`), annotation
inference (`infer`), type coverage (`coverage`), ignore management (`suppress`),
stub generation (`stubgen`), and an independent Type Server Protocol (`tsp`)
server. These are not wrapped by this library's `Session` API.

Use structured output for programmatic CLI diagnostics:

```bash
pyrefly check --output-format=json main.py
pyrefly dump-config main.py
pyrefly lsp --help
```

See [IDE features](https://pyrefly.org/en/docs/IDE-features/),
[integration limitations](../../lsp_types/pyrefly/KNOWN_LIMITATIONS.md), and
[the 1.3.0 release](https://github.com/facebook/pyrefly/releases/tag/1.3.0).
