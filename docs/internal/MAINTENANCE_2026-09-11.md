# Maintenance — September 11, 2026

## Release close-out

[PR #49](https://github.com/Mazyod/lsp-python-types/pull/49) merged into `main` after
lint and all six Python 3.12/3.13/3.14 × Pyright/basedpyright jobs passed.
[CI run](https://github.com/Mazyod/lsp-python-types/actions/runs/34591505276).

Published **0.24.0** to [PyPI](https://pypi.org/project/lsp-types/0.24.0/) using the
existing release workflow, with wheel/sdist and attestations on the
[GitHub release](https://github.com/Mazyod/lsp-python-types/releases/tag/v0.24.0).
A fresh isolated installation from PyPI passed the semantic-modifier smoke check.
The merge also triggered the [playground deployment](https://github.com/Mazyod/lsp-python-types/actions/runs/34591652483)
for [the live site](https://mazyod.com/lsp-python-types/).

## Release snapshot

Checked live registries and tagged releases, rather than cached search results.
Python lockfile: Pyrefly **1.2.0 → 1.3.0**, ty **0.0.75 → 0.0.80**,
Zuban **0.9.2 → 0.9.3**. Separately installed Microsoft Pyright **1.1.414** and
basedpyright **1.40.1**. Refreshed all resolvable Python dependencies, including
datamodel-code-generator **0.76.0 → 0.79.0**, and declared its formatter extras.
Compatibility floors remain unchanged; the lock records the tested versions.

Browser packages: browser-basedpyright **1.28.1 → 1.40.1**, TypeScript **7.0.2**,
Vite **8.3.0**, JSON-RPC **9.0.2**, LSP protocol **3.18.3**, DOMPurify **3.4.15**.
Monaco remains **0.56.0**. Pyrefly WASM is pinned to **1.3.0** and ty's WASM source
to **0.0.80**, both with SHA-256 checks. The browser UI correctly names basedpyright.

Release sources and comparisons: [field guide](research/landscape.md),
[Pyrefly investigation](research/pyrefly.md).

## What the investigation changed

- **Highlighting:** Pyrefly 1.3 emits five new string modifiers. Appended them to
  its fallback legend and the canonical legend, preserving existing indices.
  A wire-bit regression check and live server test cover all five. ty now
  advertises `operator` and `regexp` token types; the canonical legend already
  handles both. Updated the [token reference](../SEMANTIC_TOKENS.md).
- **Configuration:** updated Pyrefly severities, presets, inference, multi-platform
  settings and baselines; ty import-analysis controls, strictness, per-file
  overrides, script exclusion and output formats; Zuban `auto` mode. Refreshed
  backend limitation documents with positive-control probes and explicitly
  marked older evidence. Removed obsolete Pyrefly configuration advice.
- **Pyright distinction:** Microsoft Pyright lacks semantic tokens and omits
  optional server metadata that basedpyright supplies. Four old test assumptions
  were specific to the fork. Tests now check the correct behavior for each;
  CI explicitly selects both distributions and each Python interpreter.
- **Protocol generation:** upstream adds partial-result tokens to inline values,
  inlay hints and inline completion requests. Regenerated the public types and
  removed generated timestamps so repeated builds produce identical files.
- **Browser integration:** fixed WASM copying/URLs, repeated ty logger setup,
  inconsistent Python targets and diagnostic races around edits/backend switches.
  CI now fetches/builds and smoke-tests pinned WASM before producing the site.
- **Presentation:** replaced the long README with a ~425-word overview and one
  pixel-art party banner. Usage details and the feature matrix moved into docs.
  [Artwork and generation prompt](../../assets/images/README.md) are in the repo.

Pyrefly's configured regex/mock-target checks caught two errors that strict
Pyright did not in the same CLI probe. This is evidence for specific extra
checks, not an overall winner. ty's incremental architecture and type narrowing,
Zuban's Mypy migration/editor inference, and basedpyright's controls provide more
useful personalities than invented performance or reliability scores.

## Validation

Host: Linux x86_64, Python **3.12.14**. Commands use `uv`; npm servers were installed
in separate temporary prefixes, with the intended binary first in `PATH`.

- Full suite with basedpyright: **251 passed, 1 xfailed**. The expected exception
  is ty's variable-name hover assertion; ordinary hover passes.
- Microsoft Pyright separately: **35 passed** (`PYRIGHT_PACKAGE=pyright`, `-k Pyright`).
- `uvx pyright --pythonpath .venv/bin/python .`: **0 errors, warnings or information**.
- Ruff lint and formatting checks: **passed**; `git diff --check`: **passed**.
- `uv build`: wheel and sdist built successfully during local validation;
  the subsequent release workflow published 0.24.0 as recorded above.
- Schema generation: all five generated files reproduced **byte-for-byte**.
  `make` was unavailable, so the Makefile's recipes were run directly.
- Backend probes confirmed completion-documentation enrichment with Pyright,
  basedpyright and Zuban, Pyrefly's echo even after stripping metadata, and ty's
  `-32601` rejection. The suite now checks these behaviors explicitly.
- WASM tests: **2 passed**, exercising errors, hover and clearing after edits.
- Playground production build: **passed**; `npm audit`: **0 vulnerabilities**;
  `npm outdated`: **no entries**.
- Chromium **153** / Playwright **1.63.0**: rendered diagnostics, hover and clearing
  passed across basedpyright → Pyrefly → ty → Pyrefly → ty → basedpyright, including
  repeated WASM initialization, with no console/page errors. Rapid backend
  selection also preserved the final choice.
- `concurrency.test.mjs`: **passed** controlled late-result, edit-during-debounce,
  adapter-switch/detach, diagnostic-version, superseded-request, timeout and
  disposal checks. Timed-out requests no longer return old cached diagnostics.

The [runbook](FEATURE_VERIFICATION.md) contains reproducible commands, including
the optional browser regression script without a new project dependency.

## Limits and follow-up

Local Python testing used 3.12; the subsequent PR CI passed on 3.12, 3.13 and
3.14 with both Pyright distributions. The artwork and browser assets were inspected
locally before release. basedpyright's browser worker still loads
from pinned jsDelivr URLs. ty WASM requires Rust and a native compiler; this run
built it in an isolated Node 24 container. Its optimized WASM is about 18 MB,
and Pyrefly's about 14 MB; generated modules stay ignored and CI rebuilds them.

The existing Monaco dynamic-import bundler warning remains harmless. The
code generator also emits a formatter deprecation warning even with the extras
explicitly declared; generated output and validation succeed. Monaco's native
LSP client still lacks configurable initialization and disposal in the installed
0.56.0 artifact, so migration remains deferred (see [archived integration notes](REFERENCE_HISTORY_2026-09-11.md)).

These checks establish the tested integration behaviors, not full conformance or
an independent speed leaderboard. CLI, LSP, TSP and browser WASM features remain
separate in the evidence. No backend is labeled universally fastest or fragile.
