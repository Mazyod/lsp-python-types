# Maintenance — October 10, 2026

## Release scope

Monthly maintenance follows [the feature-verification runbook](FEATURE_VERIFICATION.md)
and [documentation policy](DOCUMENTATION.md). Work used the isolated
`codex/maintenance-2026-10-10` worktree. The existing publication workflow applied
a minor bump to **0.25.0** after merge and CI; publication and deployment receipts
belong in the close-out below.

## Version and source checks

Live PyPI JSON and npm metadata agreed with tagged upstream releases:

| Backend | Previous lock / npm check | Current stable |
|---|---|---|
| Microsoft Pyright | 1.1.414 | 1.1.414 |
| basedpyright | 1.40.1 | 1.40.2 |
| Pyrefly | 1.3.0 | 1.3.2 |
| ty | 0.0.80 | 0.0.86 |
| Zuban | 0.9.3 | 0.10.0 |

Release sources: [Pyright](https://github.com/microsoft/pyright/releases/tag/1.1.414),
[basedpyright](https://github.com/DetachHead/basedpyright/releases/tag/v1.40.2),
[Pyrefly](https://github.com/facebook/pyrefly/releases/tag/1.3.2),
[ty](https://github.com/astral-sh/ty/releases/tag/0.0.86), and
[Zuban](https://docs.zubanls.com/en/latest/changelog.html).
Pyrefly's patch fixes inference after assignments from `Any`; basedpyright fixes
browser typeshed packaging. Zuban changes forward-reference resolution and
auto-import handling. ty's intervening releases include LSP and inference fixes,
Python 3.15 fallback targeting, and
[GHSA-vxvm-j4xq-q7m4](https://github.com/astral-sh/ty/security/advisories/GHSA-vxvm-j4xq-q7m4).
Raised the ty extra's floor to **0.0.84**, the patched release. Other compatibility
floors remain unchanged.

`uv sync --all-extras --upgrade` refreshed the lock, including
datamodel-code-generator **0.79.0 → 0.83.0**, Black **26.5.1 → 26.10.1** and
Pydantic **2.13.5 → 2.14.0**. Updated setup-uv to **10.3.0** and setup-node to
**7.1.0** in the existing workflows.

## Schemas and integration boundaries

- Downloaded all three upstream schemas/models and ran the Makefile recipes
  directly because `make` is unavailable. The protocol model and generated
  protocol types are unchanged. Pyright's current upstream schema adds optional
  `maxCodeComplexity` (integer, default/minimum 768); regeneration adds that field
  to its configuration TypedDict. This is an upstream schema addition, not a
  claim that the installed stable binaries implement it.
- Repeated generation and compared SHA-256 digests: all five generated files
  reproduced byte-for-byte. The formatter-extra deprecation warning persists;
  Black/isort extras are already declared and generation succeeds.
- Compared Pyrefly's tagged `base.rs`, `config.rs`, `error_kind.rs` and
  `semantic_tokens.rs` with 1.3.0: unchanged. ty's release-source option fields,
  severities and output formats match the hand-written schema; its Python target
  is inferred from project/environment settings, falling back to 3.15. Zuban's
  documented modes and configuration remain compatible.
- Extracted live legends: basedpyright **15 types / 9 modifiers**, ty
  **17 / 4**, Zuban **23 / 8**. Pyrefly still omits its legend from initialization;
  its fallback and five string modifiers remain valid. Canonical indices did
  not change. Public legend headings now identify backends; version inventories
  stay in this record and the runbook.
- Completion tests still establish documentation enrichment with both Pyright
  distributions and Zuban, Pyrefly's echo, and ty's `-32601` error. A separate
  Pyrefly probe stripped `detail` and `documentation` before resolution and still
  received an unchanged item.
- ty initialization probes compared `unresolved-import="ignore"` with the
  misspelled `unresolved_import`: only the correct spelling suppresses the import
  error; both retain an independent assignment-error control. Default workspace
  and file-watching warnings remain. Tagged server routing still lacks a
  `workspace/didChangeConfiguration` handler; workspace-folder/config-file
  refresh changes do not remove this integration limit.
- Zuban still skips a constrained TypeVar function's assignment error and an
  unused ignore, while detecting the same error in an upper-bounded function
  and at module scope. With `typeCheckingMode="off"` and
  `disableLanguageServices=True`, initialization drops diagnostic, hover and
  completion providers; direct requests still return results. Default settings
  advertise all three providers and return the same positive controls.
- Pyrefly's opt-in regex and patch-target checks still diagnose `re.compile("[")`
  and `patch("math.nonexistent_symbol")`. Disabling both removes those diagnostics
  while preserving an independent bad-assignment control.

## Browser refresh

Updated Monaco **0.56.0 → 0.57.0**, Vite **8.3.0 → 8.3.4**, JSON-RPC
**9.0.2 → 9.0.3**, LSP protocol **3.18.3 → 3.18.4**, and DOMPurify
**3.4.15 → 3.4.16**. TypeScript remains **7.0.2**. The external
browser-basedpyright worker is pinned to **1.40.2**.

The DOMPurify refresh also fixes the repository's open
[Dependabot alert #34](https://github.com/Mazyod/lsp-python-types/security/dependabot/34)
([GHSA-p98j-92pf-mc4p](https://github.com/advisories/GHSA-p98j-92pf-mc4p)).
Raised the existing override to `^3.4.16` so its floor excludes the affected
3.4.13–3.4.15 releases; the lock already resolved the patched 3.4.16 artifact.

Pinned WASM: Pyrefly **1.3.2** release archive and ty **0.0.86** source archive,
with their upstream SHA-256 values verified before extraction/build. ty builds
in an isolated Node **24.21.0** container with Rust **1.99.0**, a native compiler and
wasm-pack **0.15.0**. Generated assets remain ignored. Monaco 0.57.0's bundled
`MonacoLspClient` still exposes only its transport constructor, with no public
initialization-parameter or disposal API; the existing adapter remains in use.

## Validation

Host: Linux x86_64, Python **3.13.15**, uv **0.12.22**, Node **22.23.3**.
Both npm LSP distributions were installed in separate temporary prefixes.

```sh
uv sync --all-extras --upgrade
PATH=/tmp/lsp-basedpyright-2026-10-10/node_modules/.bin:$PATH uv run pytest tests -q -ra
PYRIGHT_PACKAGE=pyright PATH=/tmp/lsp-pyright-2026-10-10/node_modules/.bin:$PATH \
  uv run pytest tests -k Pyright -q -ra
uvx pyright --pythonpath .venv/bin/python .
uvx ruff check .
uvx ruff format --check --exclude '*.md' .
uv build
PATH=/tmp/lsp-basedpyright-2026-10-10/node_modules/.bin:$PATH \
  uv run python examples/extract_semantic_legends.py
git diff --check
```

- Full suite: **251 passed, 1 xfailed**. The existing ty recycle-hover assertion
  expects a variable name; ordinary type-only hover still passes. No Linux skips.
- Separate Microsoft Pyright suite: **35 passed, 217 deselected**.
- Pyright: **0 errors, warnings or information**. Ruff lint and Python formatting
  passed. Ruff **0.17.0** now also formats Markdown code fences; the formatting
  command excludes Markdown to preserve existing examples and historical records.
- Wheel and source distribution built successfully; whitespace and local
  documentation link/anchor checks passed. Read the complete README user-guide
  path; public guides contain no internal-record links.
- `npm update`, the Monaco minor update, `npm audit` and `npm outdated` completed:
  **0 vulnerabilities**, **no outdated entries**.
- Playwright **1.64.0** / Chromium **156**: `concurrency.test.mjs` passed controlled
  edit-during-debounce, late-result, switch/detach, diagnostic-version,
  superseded-request, timeout and disposal checks.
- `npm run fetch-wasm` verified both archive checksums; a second run reused the
  matching versions. `npm run test:wasm`: **2 passed**. `npm run build`: **passed**,
  with both `dist/pyrefly` and `dist/ty` assets present at the configured Pages
  base path. The existing ineffective-Monaco-dynamic-import warning remains;
  Vite also reports build plugin timings. Neither prevented the browser checks.
- `browser.test.mjs` passed production markers, hover and error clearing across
  basedpyright → Pyrefly → ty → Pyrefly → ty → basedpyright, including repeated
  WASM initialization and rapid selections preserving the final backend. No
  console/page errors. Pyrefly's WASM is **13,739,184 bytes**; ty's is
  **19,481,646 bytes**.

## Release close-out

[PR #58](https://github.com/Mazyod/lsp-python-types/pull/58) merged as
`3390dcac5298735ca520cd9be342141f19ac5d07` after lint/type checking and all six
Python 3.12/3.13/3.14 × Microsoft Pyright/basedpyright jobs passed
([PR tests](https://github.com/Mazyod/lsp-python-types/actions/runs/38063468162),
[PR lint](https://github.com/Mazyod/lsp-python-types/actions/runs/38063468137)).
The same checks passed on `main`
([tests](https://github.com/Mazyod/lsp-python-types/actions/runs/38063592732),
[lint](https://github.com/Mazyod/lsp-python-types/actions/runs/38063592683)).
GitHub marked Dependabot alert #34 **fixed** after the merge.

The existing [publication workflow](https://github.com/Mazyod/lsp-python-types/actions/runs/38063698023)
published [lsp-types 0.25.0](https://pypi.org/project/lsp-types/0.25.0/).
The [GitHub release](https://github.com/Mazyod/lsp-python-types/releases/tag/v0.25.0)
contains the wheel, source distribution and their publication attestations.
Tag `v0.25.0` points to the workflow's version-bump commit, `8caa834`.

A fresh isolated PyPI installation with all three Python backend extras passed
diagnostics, error clearing after edits and normalized semantic tokens across
basedpyright, Pyrefly, ty and Zuban. The installed artifact contains
`maxCodeComplexity` and the ty >=0.0.84 requirement. PyPI's version-specific JSON
lists the wheel and sdist; its description matches the README exactly.
The wheel and sdist SHA-256 values match the corresponding GitHub assets.

The [playground deployment](https://github.com/Mazyod/lsp-python-types/actions/runs/38063592822)
passed its pinned WASM build, both WASM tests and production build, then deployed
to [the live site](https://mazyod.com/lsp-python-types/). Live HTTP checks confirmed
the Pages asset base path, basedpyright 1.40.2 worker pin, both WASM assets and
JavaScript glue matching the locally checked release builds. The complete
Chromium browser regression also passed against the live HTTPS site, including
diagnostics, hover, clearing errors, repeated backend switches and rapid
selections, with no console/page errors.

Before committing this close-out, rechecked the tagged source: **251 passed,
1 existing ty xfail**, zero Pyright errors/warnings/information, Ruff lint and
Python formatting passed. The original main worktree remains undisturbed.
