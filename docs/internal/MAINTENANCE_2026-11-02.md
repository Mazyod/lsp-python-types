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
