# Feature verification and maintenance runbook

Run this after backend releases, dependency updates or changes to `Session`.
Follow [the documentation policy](DOCUMENTATION.md). Keep evidence here and in
dated internal records; publish concise capabilities and practical limits in user guides.

## 1. Update and record versions

Check live PyPI/npm metadata and tagged upstream release notes. Search indexes can
lag a release. Prefer stable releases; distinguish an LSP binary from a CLI,
editor extension, TSP server or browser WASM package.

```sh
uv sync --all-extras --upgrade
uv run pyrefly --version
uv run ty --version
uv run zuban --version
npm view pyright version
npm view basedpyright version
```

Commit `uv.lock` with the dependency changes. Minimum supported versions in
`pyproject.toml` are compatibility floors, not the versions verified in this run;
raise them only if a change requires it. Generate schemas from upstream with:

```sh
make generate-latest-types
```

If `make` is unavailable, execute its recipes directly (`uv run` / `uvx`).
Review the schema and generated diff; don't edit generated types manually. Repeat
generation to check reproducibility. The recipes disable timestamps and explicitly
select Black/isort before Ruff formatting.

## 2. Test both Pyright distributions

`PyrightBackend` launches `pyright-langserver`. Both npm distributions provide
that executable, so install them in **separate directories**:

```sh
npm install --prefix /tmp/lsp-basedpyright basedpyright@1.40.1
npm install --prefix /tmp/lsp-pyright pyright@1.1.414
PATH=/tmp/lsp-basedpyright/node_modules/.bin:$PATH uv run pytest tests -q
PYRIGHT_PACKAGE=pyright PATH=/tmp/lsp-pyright/node_modules/.bin:$PATH \
  uv run pytest tests -k Pyright -q
uvx pyright --pythonpath .venv/bin/python .
uvx ruff check .
```

Update those exact npm versions on the next maintenance run. `PYRIGHT_PACKAGE`
selects the tests' expected Microsoft behavior; it does not choose the executable.
The default test expectation is basedpyright. CI tests both distributions on Python
3.12, 3.13 and 3.14; npm versions float there, while Python installs use the lock.

Review every failure, xfail and skip. A passing echo of a completion item does not
prove resolution adds documentation. Similarly, client capabilities describe what
**we advertise**, not what the server implements. Inspect `initialize` responses
and send a real request with a control case when validating a claim.

## Verified Session features

Snapshot **2026-09-11**: Pyright 1.1.414, basedpyright 1.40.1, Pyrefly 1.3.0,
ty 0.0.80, Zuban 0.9.3. “Yes” means the named integration test passes for its
fixture, not comprehensive conformance for every Python program.

| Feature | Pyright | basedpyright | Pyrefly | ty | Zuban |
|---|---|---|---|---|---|
| Diagnostics | Yes | Yes | Yes | Yes | Yes |
| Hover | Yes | Yes | Yes | Type only | Yes |
| Completion | Yes | Yes | Yes | Yes | Yes |
| Completion resolution | Adds docs | Adds docs | Echo | Error -32601 | Adds docs |
| Signature help | Yes | Yes | Yes | Yes | Yes |
| Rename | Yes | Yes | Yes | Yes | Yes |
| Semantic tokens | Error -32601 | Yes | Fallback legend | Yes | Yes |

Evidence lives in `tests/test_session.py`: `test_session_diagnostics`,
`test_session_hover`, `test_session_completion`, `test_session_signature_help`,
`test_session_rename`, and the `test_session_semantic_tokens*` tests. Completion
resolution checks actual added docstrings, the Pyrefly echo and ty's error.
Microsoft Pyright omits optional `serverInfo` and semantic-token metadata;
metadata/recycling tests explicitly cover that behavior.

The single expected failure is `test_session_warmup_on_recycle[ty]`, whose
variable-name assertion does not match ty's type-only hover. Normal hover works.

Go to definition, references, code actions, formatting and broader upstream
features are **not verified by this Session suite**. The low-level `LSPProcess`
API exposes requests, but exposure alone does not establish server support.

## 3. Recheck the integration boundaries

```sh
PATH=/tmp/lsp-basedpyright/node_modules/.bin:$PATH \
  uv run python examples/extract_semantic_legends.py
rg -n 'xfail|skip' tests
```

Compare legends with [the token reference](../SEMANTIC_TOKENS.md) and tagged source.
Pyrefly 1.3 still omits its provider from initialization; it needs the fallback
legend. `tests/test_semantic_tokens.py` checks that its five new string modifiers
survive normalization, including a live server fixture. Append canonical entries
so existing editor indices stay stable. ty 0.0.80 appends `operator` and `regexp`
token types, already covered by the canonical legend.

Reprobe versioned limitations with positive controls before advancing their dates:
[Pyrefly](../../lsp_types/pyrefly/KNOWN_LIMITATIONS.md),
[ty](../../lsp_types/ty/KNOWN_LIMITATIONS.md),
[Zuban](../../lsp_types/zuban/KNOWN_LIMITATIONS.md).
Check manual config schemas against tagged source/docs, including severity values,
nested sections and renamed/deprecated settings. Keep historical evidence labeled.

## 4. Refresh the browser playground

From `playground/`:

```sh
npm update
npm audit
npm run fetch-wasm
npm run test:wasm
npm run build
```

Review the pinned releases/checksums in `fetch-wasm.sh`; `npm update` alone cannot
update WASM or the browser-basedpyright CDN worker. ty's source build needs a Rust
toolchain, the WASM target and a native compiler. Pyrefly has a release WASM archive.
Verify actual browser diagnostics, hover and edits for every engine; successful
TypeScript compilation does not prove workers or WASM load. Test the configured
GitHub Pages base path and confirm the build includes `dist/pyrefly` and `dist/ty` assets.

For the optional browser regression check, install Playwright outside the project
and run the production preview in another terminal:

```sh
npm install --prefix /tmp/lsp-browser-check playwright
/tmp/lsp-browser-check/node_modules/.bin/playwright install chromium
npm run preview -- --host 127.0.0.1
# In another terminal, from playground/:
PLAYWRIGHT_MODULE=/tmp/lsp-browser-check/node_modules/playwright/index.mjs \
  node browser.test.mjs
```

The deterministic concurrency check uses Vite's dev modules to control completion
order, including late diagnostics, edits during debounce and adapter disposal:

```sh
npm run dev -- --host 127.0.0.1
# In another terminal, from playground/:
PLAYWRIGHT_MODULE=/tmp/lsp-browser-check/node_modules/playwright/index.mjs \
  node concurrency.test.mjs
```

## 5. Update public guidance and internal evidence

Update the public feature descriptions, semantic legends and actionable
limitations when behavior changes. Use direct statements, preserve the character
banner and use emojis sparingly. Keep compatibility versions that affect usage;
keep verification dates and tested-version inventories here.

Save commands, results, release sources, unresolved issues and environment details
in a dated maintenance record under `docs/internal/`. Keep detailed research in
`docs/internal/research/`. Public pages must not link to these records or this
runbook. Do not turn upstream benchmarks or test elapsed time into a speed ranking.

Before publishing, follow the README links and read each destination as a user.
Remove investigation narrative, indecisive language and repeated qualifications;
retain real limitations, experimental status and useful upstream references.
Check local links and anchors after moving documents. Use absolute GitHub links
and a raw image URL in the README so the PyPI description renders correctly.

For documentation releases, run the required tests, type check and lint; merge
only after CI passes. Use the existing `publish.yml` workflow with a patch bump
when the PyPI README needs updating. Deploy the playground through its existing
workflow when requested or when its assets change; no dependency or schema refresh
is needed for prose-only changes. Record publication and deployment results in the
internal ledger, never in the README.
