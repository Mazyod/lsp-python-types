# Pyrefly — the artificer 🔧

Pyrefly brings specialized checks and framework knowledge to Python analysis.
It understands same-file Django reverse relations, SQLAlchemy updates and
PyTorch registered attributes, alongside configurable validation for literal regexes and
`mock.patch` targets. [Feature release](https://github.com/facebook/pyrefly/releases/tag/1.3.0).

## Enable specialized checks

Enable these diagnostics in `pyrefly.toml`:

```toml
[errors]
regex = "error"
missing-attribute-patch-target = "error"
```

Run `uv run pyrefly check probe.py` on this file to report an invalid regex
and a missing patch target:

```python
import re
from unittest.mock import patch

re.compile("[")
patch("math.nonexistent_symbol")
```

To apply the same settings in a session, pass
`options={"errors": {"regex": "error", "missing-attribute-patch-target": "error"}}`
to `Session.create()`. Pyrefly accepts `pyrefly.toml` and `[tool.pyrefly]` in
`pyproject.toml`; this backend writes `pyrefly.toml`.
[Configuration reference](https://pyrefly.org/en/docs/configuration/).

## Editor tools

Pyrefly provides diagnostics, hover, completion, signature help, rename and
semantic tokens through [`Session`](../USAGE.md). Initial completion items
include type details and documentation; `resolve_completion()` returns the
item unchanged.

The library supplies Pyrefly's semantic-token legend automatically, including
its string modifiers. Use `get_semantic_tokens(normalize=True)` for the shared
[editor legend](../SEMANTIC_TOKENS.md).

Use the [typed LSP API](../USAGE.md#low-level-stdio) for workspace symbol search,
call hierarchy and references. Pyrefly’s editor integration also provides
Change Signature.
[IDE features](https://pyrefly.org/en/docs/IDE-features/).

## Experimental tools 🧪

Tensor-shape analysis for JAX, NumPy and PyTorch, and DataFrame schema checking
are experimental. Their APIs can change. The former `@shaped_array` API has
been removed. [Release details](https://github.com/facebook/pyrefly/releases/tag/1.3.0).

This backend runs `pyrefly lsp`. Pyrefly's CLI commands (`infer`, `coverage`,
`suppress`, `stubgen`, `init`) and TSP server are separate tools.
See [backend details](../../lsp_types/pyrefly/KNOWN_LIMITATIONS.md) for configuration
and completion behavior, or [compare the party](landscape.md) to choose a backend.
