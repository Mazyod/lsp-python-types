# Maintenance — November 17, 2026

## Scope and versions

Followed [the runbook](FEATURE_VERIFICATION.md) in the isolated
`codex/maintenance-2026-11-17` worktree. The main checkout and its unrelated
`.claude/` worktree were preserved. This run refreshes dependencies, browser
assets, ty configuration guidance, and the existing comparisons and benchmarks.
No runtime API or compatibility floor changes are required; publish a patch.

Live PyPI JSON, npm metadata and tagged upstream releases agree:

| Backend | Previous | Current stable |
|---|---|---|
| Microsoft Pyright | 1.1.414 | 1.1.414 |
| basedpyright | 1.40.2 | 1.40.2 |
| Pyrefly | 1.4.0 | 1.4.1 |
| ty | 0.0.95 | 0.0.104 |
| Zuban | 0.10.2 | 0.10.2 |

Sources: [Pyright](https://github.com/microsoft/pyright/releases/tag/1.1.414),
[basedpyright](https://github.com/DetachHead/basedpyright/releases/tag/v1.40.2),
[Pyrefly](https://github.com/pyrefly-org/pyrefly/releases/tag/1.4.1),
[ty](https://github.com/astral-sh/ty/releases/tag/0.0.104), and
[Zuban](https://docs.zubanls.com/en/latest/changelog.html).
Pyrefly's patch fixes its coverage CLI; its configuration and semantic-token
source are unchanged except the crate version. Its repository now redirects to
`pyrefly-org/pyrefly`; the WASM download uses that canonical location.

Reviewed all ty releases from 0.0.96 through 0.0.104: inference and memory fixes,
completion fixes, pytest-plugin fixture resolution, file-rename support and
diagnostic-rule renames. These upstream additions do not expand the verified
`Session` method inventory. `unresolved-import` became `import-not-found` in
[0.0.97](https://github.com/astral-sh/ty/releases/tag/0.0.97); the public example
uses the current name and gives the older-version spelling.

`uv sync --all-extras --upgrade` also refreshed datamodel-code-generator
0.87.0 → 0.97.0, pytest-asyncio 1.4.1.post1 → 1.5.0, Pydantic 2.14.2 → 2.14.3,
coverage 7.17.0 → 7.17.3 and smaller transitive updates. tomlkit remains 0.15.2.
setup-uv 10.3.3 and setup-node 7.1.0 remain current.

## Schemas and integration boundaries

- Ran the Makefile's download/generation recipes directly because the host's
  `make` shim has no installed version. Upstream schemas and all generated files
  are unchanged. Repeated the complete pipeline; SHA-256 checks matched all
  five generated files. The existing Black/isort-extra deprecation warning
  remains despite declared extras; generation succeeds.
- Compared ty's exact release-source `ty_project/metadata/options.rs` against
  0.0.95. No typed option fields changed. Rule alias handling and diagnostics
  changed upstream; the free-form rule mapping already accepts the new names.
- Live ty initialization probes: both `import-not-found` and its old alias
  suppress a missing import; `import_not_found` does not. All three retain an
  independent assignment error. A separate isolated ty 0.0.84 installation
  confirms the documented legacy spelling at the supported floor.
- ty return inference `never` reports only the assignment control; `always`
  also rejects assigning the result of a string-returning unannotated function
  to an integer. Release source still has no configuration-notification route
  or completion-item-resolution handler. Workspace/file-watching limits remain.
- Zuban still omits constrained-TypeVar body errors and unused-ignore warnings,
  while diagnosing the same assignment inside an upper-bounded function and at
  module scope. With type checking and language services disabled, the server
  removes advertised providers but still answers direct diagnostics, hover and
  completion requests.
- Pyrefly's opt-in regex and patch-target checks report an invalid pattern and
  a missing target; disabling those checks leaves only the assignment control.
  Completion resolution still echoes an item after removing its documentation
  and detail. Existing integration tests establish added documentation from
  both Pyright distributions and Zuban, and ty's `-32601` response.
- Live legends are unchanged: basedpyright 15 types / 9 modifiers, ty 17 / 4,
  Zuban 23 / 8 and Pyrefly fallback 23 / 19. Pyrefly's default full stream still
  omits its provider. `augmentsSyntaxTokens=True` advertises a legend identical
  to the fallback but omits string tokens; the false control returns strings.
  Existing tests cover all eight string modifiers and their normalization.

## Python validation and benchmarks

Host: Linux x86_64, AMD Ryzen 5 5500U (6 cores / 12 threads), Python 3.13.15,
uv 0.13.8, Node 22.23.5. Separate npm prefixes under
`/tmp/lsp-maintenance-2026-11-17/` select each Pyright distribution.

```sh
PATH=/tmp/lsp-maintenance-2026-11-17/basedpyright/node_modules/.bin:$PATH \
  uv run pytest tests -q -ra --log-file=/tmp/lsp-maintenance-2026-11-17/pytest-detail.log --log-file-level=INFO
PYRIGHT_PACKAGE=pyright PATH=/tmp/lsp-maintenance-2026-11-17/pyright/node_modules/.bin:$PATH \
  uv run pytest tests -k Pyright -q -ra --log-file=/tmp/lsp-maintenance-2026-11-17/ms-detail.log --log-file-level=INFO
uvx pyright --pythonpath .venv/bin/python .
uvx ruff check .
uvx ruff format --check --exclude '*.md' .
uv build
git diff --check
```

Full suite: **251 passed, 1 expected ty hover failure**, no skips. Separate
Microsoft suite: **35 passed, 217 deselected**. The expected failure remains
the recycled-session variable-name assertion; ty returns a type-only hover.
Pyright: **0 errors, warnings or information**. Ruff lint/formatting and
wheel/source builds passed.

The existing `TestLSPProcessPoolBenchmarks` ran unchanged. Seconds below are the
tests' reported means (three creation samples, five warmed reuse samples versus
three fresh samples) or the total for a three-session concurrent batch:

| Server | Creation pooled / fresh | Warm reuse + hover / fresh | Concurrent pooled / fresh |
|---|---:|---:|---:|
| Microsoft Pyright | 0.052 / 0.354 | 0.259 / 0.656 | 0.763 / 0.779 |
| basedpyright | 0.061 / 0.363 | 0.263 / 0.660 | 0.789 / 0.876 |
| Pyrefly | 0.002 / 0.064 | 0.028 / 0.148 | 0.163 / 0.161 |
| ty | 0.002 / 0.016 | 0.003 / 0.016 | 0.017 / 0.021 |
| Zuban | 0.002 / 0.050 | 0.015 / 0.051 | 0.050 / 0.061 |

Pyrefly's thread-option benchmark reported 0.051 / 0.050 / 0.050 / 0.052 seconds
for 0 / 1 / 2 / 4 threads. The backend passes thread counts through CLI flags;
Pyrefly also warns about the redundant `threads`/`verbose` keys in its TOML.
The tiny fixture does not establish a preferred thread count.

Warm reuse reduces lifecycle costs in these fixtures. Cold concurrent creation
does not promise a pooling gain (Pyrefly was slightly slower). These are small
single-run integration measurements on a shared host, not whole-project checking
or incremental-analysis rankings. Python timings were captured before Rust
compilation began. No comparable historical local timings were recorded in the
previous maintenance ledger, so this run makes no before/after speed claim.

Revisited [Astral's benchmark context](https://astral.sh/blog/ty),
[Zuban's capabilities](https://docs.zubanls.com/en/latest/features.html), and
[basedpyright's editor additions](https://docs.basedpyright.com/latest/benefits-over-pyright/pylance-features/).
The historical CLI and incremental LSP workloads remain distinct from these
session benchmarks. The public backend comparisons need no new ranking or
feature claims. All eight README-linked public documents were read and passed
local link/anchor checks; none links to internal records. The character banner
and backend personalities are unchanged.

## Browser refresh

Updated Vite 8.3.5 → 8.3.8 and DOMPurify 3.4.17 → 3.4.18. Monaco 0.57.0,
TypeScript 7.0.2, protocol 3.18.5, JSON-RPC 10.0.0 and browser-basedpyright 1.40.2
remain current. `npm audit`: **0 vulnerabilities**; `npm outdated`: no entries.
GitHub reports **no open Dependabot alerts**, including the alerts awaiting
refresh at the previous close-out.

Pinned Pyrefly 1.4.1 WASM and ty 0.0.104 source archives to the SHA-256 digests
published with their GitHub releases. Both archive checks passed. The isolated
Node 24 build installs Rust stable 1.100.0; ty's release workspace selects its
pinned Rust 1.99.0. wasm-pack remains 0.15.1; generated assets remain ignored.

The existing Playwright concurrency checks passed edits during debounce, late
results, backend switching/detaching, diagnostic versions, superseded requests,
timeouts and disposal.

```sh
cd playground
npm update
npm audit
npm outdated
npm run fetch-wasm
npm run test:wasm
npm run build
# With Vite dev and production preview servers running:
PLAYWRIGHT_MODULE=/tmp/lsp-maintenance-2026-11-17/browser/node_modules/playwright/index.mjs \
  node concurrency.test.mjs
PLAYWRIGHT_MODULE=/tmp/lsp-maintenance-2026-11-17/browser/node_modules/playwright/index.mjs \
  node browser.test.mjs
```

- WASM checks: **2 passed**, covering diagnostics, hover and error clearing.
  A second fetch reused the matching versioned assets.
- Production build passed with both WASM directories at `/lsp-python-types/`.
  Pyrefly WASM: **14,186,267 bytes**; local ty WASM: **20,634,530 bytes**.
  The existing ineffective Monaco dynamic-import warning remains.
- Playwright **1.65.1**, Chromium **159.0.8154.6**: production diagnostics,
  hover and edit clearing passed through basedpyright → Pyrefly → ty → Pyrefly
  → ty → basedpyright. Rapid selections preserved the final backend. No page
  or console errors.

## Release close-out

[PR #65](https://github.com/Mazyod/lsp-python-types/pull/65) merged as
`d48591f49540cb17427088af35ddaf88d9465be4` after all six Python
3.12/3.13/3.14 × basedpyright/Microsoft Pyright jobs and lint/type checking
passed ([PR tests](https://github.com/Mazyod/lsp-python-types/actions/runs/44018720527),
[PR lint](https://github.com/Mazyod/lsp-python-types/actions/runs/44018720532)).
The same checks passed on the merged commit
([main tests](https://github.com/Mazyod/lsp-python-types/actions/runs/44018924340),
[main lint](https://github.com/Mazyod/lsp-python-types/actions/runs/44018924404)).

The existing [publication workflow](https://github.com/Mazyod/lsp-python-types/actions/runs/44019104676)
applied a patch bump and published [lsp-types 0.26.1](https://pypi.org/project/lsp-types/0.26.1/).
Tag `v0.26.1` points to version-bump commit `5b6d783`.
The [GitHub release](https://github.com/Mazyod/lsp-python-types/releases/tag/v0.26.1)
contains the wheel, source archive and publication attestations.

A fresh isolated PyPI installation with all three extras passed diagnostics,
hover, normalized semantic tokens and error clearing after edits across
basedpyright, Pyrefly, ty and Zuban. The published ty initialization example
suppressed the missing import while retaining an independent assignment error.
The install used `uv pip install --refresh-package lsp-types` to refresh the
just-published package's cached index metadata.

The published wheel includes the updated ty guidance. PyPI's description matches
the repository README exactly. Downloaded PyPI artifacts match their metadata
and GitHub release asset SHA-256 values:

- Wheel: `5d4dbff74d27f8180c1a5e62418ae119255f338b27e8b50f543e3f9eff76d445`
- Source: `307f8792ade2532a5167122da4f310c9888fd3ca5ac3a8d71179bad6f03a033e`

The [playground workflow](https://github.com/Mazyod/lsp-python-types/actions/runs/44018924335)
passed both pinned archive checks, both WASM tests and the production build,
then deployed to [the live site](https://mazyod.com/lsp-python-types/).
Downloaded Pages artifact **14300246965** and verified its ZIP digest
`31cb316548f2e77d7f2c38e1a6660e848faca6d9e2cf4f60a5f904c47bb4967e`.
The live HTML, main JavaScript bundle, both WASM glue files and both WASM
binaries match that artifact byte-for-byte. The configured base path and
browser-basedpyright 1.40.2 pin are correct.

Deployed Pyrefly WASM is **14,186,267 bytes**, SHA-256
`5577b55bb4ec3b5d862631bb0fd3ec42ca8a424577b833d5125237a81c511077`.
Deployed ty WASM is **20,636,285 bytes**, SHA-256
`c4ae4f14c2e15e3b7cc4c9bece7a2c5cfaa6c75fb6e08eed54b197f63afdd8a0`.
The independent local ty build differs from CI, as expected for builds with
embedded source paths; deployment verification uses the actual CI artifact.

The complete Chromium regression passed on live HTTPS: diagnostics, hover,
edit clearing, repeated backend switches and rapid selections, with no page or
console errors. GitHub still reports no open Dependabot alerts.

Before committing this close-out, the tagged source passed **251 tests with
1 existing ty xfail**, zero Pyright errors/warnings/information, Ruff lint and
Python formatting. Temporary dev and preview servers were stopped.
