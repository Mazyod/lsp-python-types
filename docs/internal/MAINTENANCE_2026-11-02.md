# Maintenance — November 2, 2026

## Scope and workspace

Followed [the maintenance runbook](FEATURE_VERIFICATION.md) and
[documentation policy](DOCUMENTATION.md) in the isolated
`codex/maintenance-2026-11-02` worktree. Removed the completed October worktree
and its local close-out branch after confirming that its HEAD matched `main`,
there were no tracked or untracked changes, and only ignored build/cache files
remained. The main worktree and its unrelated `.claude/` worktree were untouched.

## Versions and sources

Live PyPI JSON and npm metadata agreed with tagged upstream releases:

| Backend | Previous | Current stable |
|---|---|---|
| Microsoft Pyright | 1.1.414 | 1.1.414 |
| basedpyright | 1.40.2 | 1.40.2 |
| Pyrefly | 1.3.2 | 1.4.0 |
| ty | 0.0.86 | 0.0.95 |
| Zuban | 0.10.0 | 0.10.2 |

Sources: [Pyright](https://github.com/microsoft/pyright/releases/tag/1.1.414),
[basedpyright](https://github.com/DetachHead/basedpyright/releases/tag/v1.40.2),
[Pyrefly](https://github.com/meta/pyrefly/releases/tag/1.4.0),
[ty](https://github.com/astral-sh/ty/releases/tag/0.0.95), and
[Zuban](https://docs.zubanls.com/en/latest/changelog.html).
Pyrefly adds configuration inheritance and string-content highlighting. ty adds
return inference controls and diagnostic baselines; Zuban fixes LSP invalidation
and improves import paths and docstrings.

`uv sync --all-extras --upgrade` refreshed the lock, including
datamodel-code-generator 0.83.0 → 0.87.0, pytest 9.1.1 → 9.2.0,
Pydantic 2.14.0 → 2.14.2 and tomlkit 0.15.1 → 0.15.2.
Updated setup-uv 10.3.0 → 10.3.3. The existing setup-node 7.1.0 and checkout v7
references remain current. Compatibility floors are unchanged except Pyrefly,
whose new token ordering requires 1.4.0 for the fallback below.

## Schemas and integration boundaries

- Downloaded the upstream protocol models and Pyright schema. The protocol
  model and generated protocol types are unchanged. Pyright adds optional
  `useDefaultExcludes`; this follows the upstream schema, without claiming
  support in the unchanged stable binaries.
- Used the Makefile's recipes directly because the `make` shim has no installed
  version. All five generated files reproduced byte-for-byte on a second run.
  The existing Black/isort-extra deprecation warning remains despite declared
  extras; generation succeeds.
- Pyrefly 1.4 inserts `escapeSequence`, `formatPlaceholder` and `formatSpecifier`
  at raw modifier bits 12–14, shifting four existing string modifiers. The
  previous fallback misdecoded the new stream and failed the existing live
  string test. Updated the fallback and appended canonical bits 19–21, keeping
  every existing canonical index stable. Both strengthened regression tests
  failed before the repair and passed afterward.
- An initialization probe with `augmentsSyntaxTokens=True` obtained the correct
  server legend but returned no string tokens. The default full stream retains
  all eight string modifiers and uses the 1.4 fallback. Raising the Pyrefly floor
  avoids silently misdecoding older servers with the new fallback.
- Compared Pyrefly's tagged configuration source. Added `site_packages_path`
  while retaining the singular alias, `extends`, `baseline_auto_update`, and
  the `column-ordered` matching mode. A live inheritance probe confirmed both
  inherited suppression and a local severity override.
- Checked ty's exact release-source `ty_project/metadata/options.rs`. Added
  `analysis.return_type_inference`, preview `baseline`, and `sarif` output.
  With inference `never`, only the independent assignment control failed;
  with `always`, the assignment from an unannotated string-returning function
  also failed. Zuban's manual schema remains compatible with its documented modes.
- Live legends: basedpyright 15 types / 9 modifiers, ty 17 / 4, Zuban 23 / 8.
  Pyrefly's fallback is 23 / 19. Only Pyrefly changed.
- Separate completion probes confirm Pyrefly still echoes an item even after
  removing its detail and documentation. Integration tests establish added
  documentation from both Pyright distributions and Zuban, and ty's `-32601`.
- ty still ignores misspelled initialization rule keys: `unresolved-import`
  suppresses the import error while `unresolved_import` does not; both retain
  an assignment-error control. Release source has no configuration-notification
  route. Its default workspace/file-watching limitations remain.
- Zuban still misses constrained-TypeVar body errors and unused ignores, while
  reporting the same assignment error in an upper-bounded function and at module
  scope. Disabled type checking/language services remove advertised providers,
  but direct diagnostics, hover and completion still return results.
- Pyrefly's enabled regex and patch-target checks diagnose an invalid pattern
  and missing patch target. Disabling them leaves only the assignment control.

## Python validation

Host: Linux x86_64, Python 3.13.15, uv 0.13.1, Node 22.23.3. Each npm LSP
distribution was installed under its own temporary prefix.

```sh
PATH=/tmp/lsp-basedpyright-2026-11-02/node_modules/.bin:$PATH uv run pytest tests -q -ra
PYRIGHT_PACKAGE=pyright PATH=/tmp/lsp-pyright-2026-11-02/node_modules/.bin:$PATH \
  uv run pytest tests -k Pyright -q -ra
uvx pyright --pythonpath .venv/bin/python .
uvx ruff check .
uvx ruff format --check --exclude '*.md' .
uv build
git diff --check
```

Full suite: **251 passed, 1 existing ty xfail**, no skips. Separate Microsoft
Pyright suite: **35 passed, 217 deselected**. Pyright: **0 errors, warnings or
information**. Ruff lint/formatting and wheel/sdist builds passed.

Read the full README user-guide path; all eight public documents passed local
link/anchor checks and contain no internal-record links. The character banner
and backend profiles are unchanged. Public changes explain the Pyrefly minimum
and its actual raw/canonical token ordering.

## Browser refresh and validation

Updated Vite 8.3.4 → 8.3.5, LSP protocol 3.18.4 → 3.18.5 and DOMPurify
3.4.16 → 3.4.17. Aligned the direct JSON-RPC dependency with protocol 3.18.5's
JSON-RPC 10.0.0 requirement; npm deduplicates them. Monaco remains 0.57.0,
TypeScript 7.0.2, and the browser-basedpyright CDN worker remains pinned to 1.40.2.

Raised the DOMPurify override floor to `^3.4.17`, the patched version for all
three open dependency alerts:
[35](https://github.com/Mazyod/lsp-python-types/security/dependabot/35),
[36](https://github.com/Mazyod/lsp-python-types/security/dependabot/36), and
[37](https://github.com/Mazyod/lsp-python-types/security/dependabot/37).
`npm audit`: **0 vulnerabilities**. `npm outdated`: **no entries**.

Pinned Pyrefly 1.4.0's WASM archive and ty 0.0.95's source archive to their
GitHub release SHA-256 digests. The fetch script verified both before extraction;
a second run reused the matching assets. Updated wasm-pack 0.15.0 → 0.15.1.
Built ty in an isolated Node 24.21.0 container: rustup installed stable 1.99.1,
then the release workspace selected its pinned Rust 1.99.0. The generated assets
remain ignored. Pyrefly WASM is **14,183,814 bytes**; ty is **19,966,393 bytes**.

```sh
cd playground
npm update
npm install
npm audit
npm outdated
npm run fetch-wasm
npm run test:wasm
npm run build
# With dev and production preview servers running in separate terminals:
PLAYWRIGHT_MODULE=/tmp/lsp-browser-check-2026-11-02/node_modules/playwright/index.mjs \
  node concurrency.test.mjs
PLAYWRIGHT_MODULE=/tmp/lsp-browser-check-2026-11-02/node_modules/playwright/index.mjs \
  node browser.test.mjs
```

- WASM tests: **2 passed**, covering diagnostics, hover and error clearing.
- Production build passed with both `dist/pyrefly` and `dist/ty` assets at the
  configured `/lsp-python-types/` base path. The existing ineffective Monaco
  dynamic-import warning remains.
- Playwright 1.64.1 / Chromium 156 passed concurrency checks for edits during
  debounce, late results, adapter switch/detach, diagnostic versions,
  superseded requests, timeouts and disposal.
- Production browser checks passed diagnostics, hover and error clearing through
  basedpyright → Pyrefly → ty → Pyrefly → ty → basedpyright. Rapid selections
  preserved the final backend. No console or page errors.

## Release close-out

[PR #64](https://github.com/Mazyod/lsp-python-types/pull/64) merged as
`fc7083d5646a3ffa14560906b77a586c6d47de81` after all six Python
3.12/3.13/3.14 × basedpyright/Microsoft Pyright jobs and lint/type checking passed
([PR tests](https://github.com/Mazyod/lsp-python-types/actions/runs/41453637453),
[PR lint](https://github.com/Mazyod/lsp-python-types/actions/runs/41453637588)).
The same checks passed on the merged commit
([main tests](https://github.com/Mazyod/lsp-python-types/actions/runs/41453909073),
[main lint](https://github.com/Mazyod/lsp-python-types/actions/runs/41453909089)).

The existing [publication workflow](https://github.com/Mazyod/lsp-python-types/actions/runs/41454232260)
applied a minor bump and published [lsp-types 0.26.0](https://pypi.org/project/lsp-types/0.26.0/).
Tag `v0.26.0` points to its version-bump commit, `293a00e`.
The [GitHub release](https://github.com/Mazyod/lsp-python-types/releases/tag/v0.26.0)
contains the wheel, source archive and publication attestations.

A fresh isolated PyPI installation with all three Python extras passed
diagnostics, error clearing after edits, hover and normalized semantic tokens
across basedpyright, Pyrefly, ty and Zuban. The installed artifact includes
`useDefaultExcludes`, the Pyrefly >=1.4.0 requirement, stable existing canonical
indices and the three new string-content modifiers, verified against live tokens.
The PyPI description matches the repository README exactly. Downloaded PyPI
artifact SHA-256 values match GitHub's release assets:

- Wheel: `7795eb334a0f91da1e69f82e99d837db0705290de2277eedc35cc75e965005ca`
- Source: `68cacf9cfff423a4c7ab5fd7e8f6ce238aa26535c57b3fb59cc9d1f6e98214ef`

The [playground workflow](https://github.com/Mazyod/lsp-python-types/actions/runs/41453909049)
verified both pinned archives, passed both WASM tests and the production build,
and deployed to [the live site](https://mazyod.com/lsp-python-types/).
Live HTTP checks confirmed the Pages base path and basedpyright 1.40.2 worker pin.
Pyrefly WASM and both JavaScript glue files match the local release builds.
ty's CI binary embeds `/home/runner/.cargo` source paths instead of the local
container's `/root/.cargo` paths; independent build hashes therefore differ.
Downloaded Pages artifact **13146267455** and verified its ZIP digest
`3a83a85fb21de926eb158ec0f4945709ff66a5b673f193adaf6e6091b2e9475e`.
The deployed ty binary matches that artifact exactly: **19,968,148 bytes**,
SHA-256 `5d203f9f4a401060d293211fb6ac43bd37e486fca3676425a61e79d74926bd14`.

The complete Chromium regression passed on the live HTTPS site: diagnostics,
hover, error clearing, repeated WASM backend switches and rapid selections,
with no console or page errors.

GitHub's dependency-graph SBOM confirms DOMPurify **3.4.17** on `main`.
Alerts #35–37 still reported `open` at close-out despite their affected range
ending at 3.4.16 and their patched version being 3.4.17. No alerts were manually
dismissed; their automatic status refresh remains pending. The installed lock
and npm audit confirm the remediation.

Before committing the close-out, rechecked the tagged source: **251 passed,
1 existing ty xfail**, zero Pyright errors/warnings/information, Ruff lint and
Python formatting passed.
