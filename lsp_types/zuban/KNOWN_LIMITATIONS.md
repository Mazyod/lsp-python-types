# Zuban Backend - Known Limitations

This document describes known limitations and behavioral differences when using the Zuban backend compared to other LSP backends (Pyright, Pyrefly, ty).

## 1. Config Written to `pyproject.toml`

**Behavior**: `ZubanBackend.write_config` adds or updates `[tool.zuban]` inside `pyproject.toml`, preserving any existing `[project]` metadata and other `[tool.*]` sections. It does not read, merge, or write `mypy.ini`, `.mypy.ini`, or `setup.cfg`.

**Why `pyproject.toml` and not a dedicated file**: Unlike Pyright (`pyrightconfig.json`), Pyrefly (`pyrefly.toml`), and ty (`ty.toml`), Zuban has no dedicated config file in its native "default" mode. Selecting Zuban's PyRight-like mode is done via `pyproject.toml`'s `[tool.zuban]` table (some settings can also be passed as LSP `initializationOptions` — see entry 4).

**Why `[tool.zuban]` and not `[tool.mypy]`**: Presence of `[tool.zuban]` puts Zuban into its recommended `default` mode (PyRight-like). `[tool.mypy]` would force the Mypy-compatible mode, which is less capable.

**Impact**: Re-invoking `write_config` replaces the previous `[tool.zuban]` table
in place; every other parsed value and section is preserved.

**Caveat — formatting is not preserved**: `write_config` is a full `tomllib` ->
`tomli_w` round-trip, so it preserves *values* but not *formatting*. Comments are
stripped, inline tables expand into sections, and arrays reflow. Because
`Session.create()` defaults to `base_path=Path(".")`, calling it from a real
project root will rewrite that project's `pyproject.toml` and drop its comments.
Pass an explicit `base_path` (a temporary directory, say) when that matters.
Pyrefly and ty are unaffected: they write dedicated `pyrefly.toml`/`ty.toml` files
that the library owns outright, rather than a file shared with the user's project.

## 2. Unused `# type: ignore` Comments Not Reported

**Limitation**: Zuban does not yet report unused `# type: ignore` comments (upstream limitation still present as of Zuban 0.9.2, per the [features documentation](https://docs.zubanls.com/en/latest/features.html)).

**Impact**: Code that accumulates stale `# type: ignore` comments will not be flagged when using this backend.

## 3. Value-Constrained `TypeVar` Function Bodies Not Type-Checked

**Limitation**: Zuban does not type-check function bodies parameterized by a
*value-constrained* `TypeVar` — `TypeVar("T", str, bytes)` or the PEP 695 form
`[T: (str, bytes)]`. Upstream lists this under "Missing Features" in the
[features documentation](https://docs.zubanls.com/en/latest/features.html), still
present as of Zuban 0.9.2.

**Not affected**: *upper-bounded* TypeVars — `TypeVar("T", bound=str)` — are
checked normally. The distinction is constraints (a tuple of alternatives)
versus a bound (a single upper limit); only the former disables body checking.

**Impact**: Type errors inside value-constrained generic functions do not surface
via diagnostics. Verified at 0.9.2: `bad: int = "definitely not an int"` inside a
`TypeVar("T", str, bytes)` body (line 7) and inside a `[T: (str, bytes)]` body
(line 2) produced no diagnostic, while the identical statement in a plain
`def plain(x: str) -> str` in the same file (lines 13 and 8 respectively) was
reported as `[assignment] Incompatible types in assignment (expression has type
"str", variable has type "int")`. The same statement inside a
`TypeVar("T", bound=str)` body (line 7) was reported.

## 4. No CLI Configuration Flags on `zuban server`

**Limitation**: `zuban server` accepts no configuration flags. `zuban server --help`
lists only `-h, --help`; a configuration argument is rejected outright, e.g.
`zuban server --mode default` -> `error: unexpected argument '--mode' found`.
(By contrast `zuban check` exposes a large flag surface including `--mode`,
`--untyped-function-return-mode`, and `--python-executable`.)

**Impact**: No functional impact on this backend — `ZubanBackend` configures Zuban
via `pyproject.toml`. Unlike the Pyrefly backend (which exposes `--verbose`,
`--threads`, `--indexing-mode` through `ProcessLaunchInfo`),
`ZubanBackend.create_process_launch_info` returns a fixed `["zuban", "server"]`.

**Configuration is not exclusively file-based.** Zuban also reads LSP
`initializationOptions` sent with `initialize`. Upstream's changelog adds these in
0.8.1 (`typeCheckingMode`, `disableLanguageServices`, `diagnosticMode`,
`pythonExecutable`) and 0.9.1 (`inlayHintMode`). `ZubanBackend` sends none, but
callers can supply them via `Session.create`'s public `initialize_params`:

    await Session.create(
        ZubanBackend(),
        initialize_params={"initializationOptions": {"diagnosticMode": "workspace"}},
    )

Confirmed to change behavior at 0.9.2 by diffing the initialize response:
`diagnosticMode="workspace"` flips `diagnosticProvider.workspaceDiagnostics` to
`true`; `typeCheckingMode="off"` drops `diagnosticProvider` entirely;
`disableLanguageServices=true` drops `hoverProvider` and sets
`completionProvider: false`. An unknown key left the response identical to
baseline, confirming these are read rather than ignored.

**Caveat**: for the two options probed this way, the change was to what Zuban
*advertises*, not to what it *answers*. With `typeCheckingMode="off"`,
`textDocument/diagnostic` still returned the same diagnostic; with
`disableLanguageServices=true`, hover and completion still returned results. A
client that gates requests on advertised capabilities sees a behavior change;
`Session`, which sends requests unconditionally, does not. The remaining options
(`diagnosticMode`, `pythonExecutable`, `inlayHintMode`) were not probed this way.

---

## Version Information

These limitations were documented based on Zuban version 0.7.0 (April 2026), last
verified on 2026-08-30 with Zuban 0.9.2 (released 2026-08-26, the newest release on
PyPI). All four entries were re-probed directly against a live `zuban server`
reporting `serverInfo {"name": "zuban", "version": "0.9.2"}`:

- **1** — a pre-existing `pyproject.toml` containing `[project]`,
  `[project.scripts]`, `[build-system]`, `[tool.ruff]`, and `[tool.foo]` (with an
  inline table and a `[[tool.foo.item]]` array-of-tables) survived a `write_config`
  call with every parsed value intact; only `[tool.zuban]` was replaced. The merge
  preserves *values*, not *formatting*: the file is a full `tomllib` -> `tomli_w`
  round-trip, so comments are stripped, inline tables expand into sections, and
  arrays are reflowed.
- **2** — a file containing two unnecessary `# type: ignore` comments produced zero
  diagnostics, while a plain type error in a control file was reported.
- **3** — a type error inside a value-constrained `TypeVar("T", str, bytes)` body
  (line 7) and inside a PEP 695 `[T: (str, bytes)]` body (line 2) went unreported,
  while the identical error in a plain function in the same file (lines 13 and 8)
  was caught. An upper-bounded `TypeVar("T", bound=str)` body (line 7) *was*
  checked.
- **4** — `zuban server --help` still lists only `-h/--help`, and
  `zuban server --mode default` fails with `error: unexpected argument '--mode'
  found`. Zuban does honor LSP `initializationOptions`; see that section.

Upstream still lists entries 2 and 3 verbatim under "Missing Features" in the
[features documentation](https://docs.zubanls.com/en/latest/features.html), and the
0.9.2 changelog records only bugfixes and conformance-test fixes. Future versions
may address some of these limitations.
