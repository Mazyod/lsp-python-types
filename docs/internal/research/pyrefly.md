# Pyrefly: the artificer with a growing toolkit

Research checked **2026-09-11**. Character metaphor describes specialization,
not a performance ranking or a claim about reliability.

## Release and direction

**1.3.0** is the current stable release. Its notes say September 10; GitHub
published it September 11 at 00:42 UTC, following the first PyPI wheel at
00:41 UTC. Cached search results still showed 1.2.0, so the live
[PyPI metadata](https://pypi.org/pypi/pyrefly/json) and
[GitHub release metadata](https://api.github.com/repos/facebook/pyrefly/releases/latest)
were checked directly.

The distinctive direction is broader code understanding. Version 1.3 adds
literal-regex and `mock.patch` validation, same-file Django reverse relations,
SQLAlchemy update checks, and PyTorch registered attributes. Its LSP adds Change
Signature, wider workspace symbol search, and cross-file hierarchy/reference
support without opening each file. Tensor-shape checking for JAX/NumPy/PyTorch
and DataFrame schema checking remain **experimental**; the previous
`@shaped_array` API was removed. These are upstream release claims, not all
features independently tested here. [1.3.0 release notes](https://github.com/facebook/pyrefly/releases/tag/1.3.0)

## A small, reproducible difference

This CLI probe was run with Pyrefly **1.3.0** and Pyright **1.1.414**, using
temporary files and explicit configurations:

```python
import re
from unittest.mock import patch
re.compile("[")
patch("math.nonexistent_symbol")
```

With the following `pyrefly.toml`, `pyrefly check probe.py` reported both an
invalid regex and a missing patch target:

```toml
[errors]
regex = "error"
missing-attribute-patch-target = "error"
```

`pyright --project . probe.py`, with `{"typeCheckingMode": "strict"}` in
`pyrightconfig.json`, reported **0 errors and 0 warnings**. This demonstrates
two particular checks, not comparative correctness across Python. An
unconfigured Pyrefly snippet reported no errors: enable the intended checks
explicitly when reproducing the comparison. These results concern CLI
diagnostics; the same fixture was not tested through LSP in this research.

## Keep the interfaces separate

The installed `pyrefly --help` confirms `infer`, `coverage`, `suppress`,
`stubgen`, configuration migration via `init`, and `tsp` alongside `lsp`.
This library starts **`pyrefly lsp`**; it does not wrap those CLI commands or
TSP. Upstream advertises richer editor refactorings and navigation than this
library's high-level `Session` methods currently expose; low-level LSP access
is a separate path. [IDE feature documentation](https://pyrefly.org/en/docs/IDE-features/)

The release's striking TSP speedups measure repeated requests in a captured
Pylance session. They are neither Pyrefly-versus-Pyright timings nor this
library's LSP latency. Do not turn them into README speed multipliers.
[Performance notes](https://github.com/facebook/pyrefly/releases/tag/1.3.0)

## Upgrade findings for this integration

- This maintenance extends the hardcoded semantic-token and canonical modifier lists with
  `byteString`, `formatString`, `rawString`, `stringPrefix`, `templateString`;
  the previous run already detected these in 1.3 prereleases. A fresh 1.3.0
  LSP probe confirmed the missing advertised legend and completion-resolution
  echo, including when detail and documentation were stripped first.
- The typed configuration now includes current severity strings in
  `ErrorConfig`, `preset`, `check_unannotated_defs`, `infer_return_types`,
  `replace_untyped_imports_with_any`, and useful baseline settings.
  `untyped_def_behavior` remains for compatibility but is marked deprecated. The tagged
  implementation explicitly names its replacements.
  [1.3.0 base configuration](https://github.com/facebook/pyrefly/blob/1.3.0/crates/pyrefly_config/src/base.rs),
  [baseline configuration](https://github.com/facebook/pyrefly/blob/1.3.0/crates/pyrefly_config/src/config.rs),
  [severity definitions](https://github.com/facebook/pyrefly/blob/1.3.0/crates/pyrefly_config/src/error_kind.rs)
- The historical `assets/lsps/pyrefly-guide.md` advice that config files
  are unreliable has been replaced. The supported files are `pyrefly.toml` and
  `[tool.pyrefly]` in `pyproject.toml`; CLI JSON output also makes its regex
  stderr parser unnecessary. More inference can analyze more dependency
  modules, so depth has a cost. [Configuration documentation](https://pyrefly.org/en/docs/configuration/)

## Character choice

Pyrefly's artificer carries a toolbelt and glowing firefly: a metaphor for broader
code analysis and specialized tools, with experimental features clearly marked.
It is not a score for speed, robustness or overall correctness.
