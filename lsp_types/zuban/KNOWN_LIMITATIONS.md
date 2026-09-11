# Zuban Backend - Known Limitations

This document describes known limitations and behavioral differences when using the Zuban backend compared to other LSP backends (Pyright, Pyrefly, ty).

## 1. Config Written to `pyproject.toml`

**Behavior**: `ZubanBackend.write_config` adds or updates `[tool.zuban]` inside `pyproject.toml`, preserving any existing `[project]` metadata and other `[tool.*]` sections. It does not read, merge, or write `mypy.ini`, `.mypy.ini`, or `setup.cfg`.

**Why `pyproject.toml` and not a dedicated file**: Unlike Pyright (`pyrightconfig.json`), Pyrefly (`pyrefly.toml`), and ty (`ty.toml`), Zuban has no dedicated config file in its native "default" mode. Selecting Zuban's PyRight-like mode is done via `pyproject.toml`'s `[tool.zuban]` table (some settings can also be passed as LSP `initializationOptions` — see entry 4).

**Why `[tool.zuban]` and not `[tool.mypy]`**: Presence of `[tool.zuban]` puts Zuban into its recommended `default` mode (PyRight-like). `[tool.mypy]` would force the Mypy-compatible mode, which preserves different Mypy-compatible defaults.

**Impact**: Re-invoking `write_config` replaces the previous `[tool.zuban]` table
in place; every other parsed value and section is preserved.

**Formatting is preserved**: `write_config` is a format-preserving `tomlkit`
edit. Only the `[tool.zuban]` table is added or replaced; comments, inline
tables, arrays-of-tables, key ordering, whitespace and line endings elsewhere in
the file survive. Comments that `tomlkit` associates with an existing
`[tool.zuban]` go with it, since that table is replaced wholesale. This matters because `Session.create()` defaults to
`base_path=Path(".")`, so the naive call operates on the caller's real
`pyproject.toml`. (Until v0.22.1 this was a `tomllib` -> `tomli_w` round-trip
that preserved values but stripped every comment.)

**The table is written even when `options` is empty**, and must be: its
*presence* is what selects Zuban's `default` mode. A project carrying
`[tool.mypy]` but no `[tool.zuban]` uses Mypy-compatible defaults, so
skipping the write would silently change its mode. Note this is observable only
through `zuban server` — the `zuban check` subcommand pins `default` mode
regardless of configuration, which makes the caveat easy to mis-verify.

## 2. Unused `# type: ignore` Comments Not Reported

**Limitation**: Zuban does not yet report unused `# type: ignore` comments (upstream limitation still present as of Zuban 0.9.3, per the [features documentation](https://docs.zubanls.com/en/latest/features.html)).

**Impact**: Code that accumulates stale `# type: ignore` comments will not be flagged when using this backend.

## 3. Value-Constrained `TypeVar` Function Bodies Not Type-Checked

**Limitation**: Zuban does not type-check function bodies parameterized by a
*value-constrained* `TypeVar` — `TypeVar("T", str, bytes)` or the PEP 695 form
`[T: (str, bytes)]`. Upstream lists this under "Missing Features" in the
[features documentation](https://docs.zubanls.com/en/latest/features.html), still
present as of Zuban 0.9.3.

**Not affected**: *upper-bounded* TypeVars — `TypeVar("T", bound=str)` — are
checked normally. The distinction is constraints (a tuple of alternatives)
versus a bound (a single upper limit); only the former disables body checking.

**Impact**: Type errors inside value-constrained generic functions do not surface
via diagnostics. Historical August 30 probe at 0.9.2: `bad: int = "definitely not an int"` inside a
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

Reconfirmed at 0.9.3 by diffing the initialize response:
`diagnosticMode="workspace"` flips `diagnosticProvider.workspaceDiagnostics` to
`true`; `typeCheckingMode="off"` drops `diagnosticProvider` entirely;
`disableLanguageServices=true` drops `hoverProvider` and removes
`completionProvider`. The historical 0.9.2 probe also found that an unknown key
left the response identical to baseline; that control was not repeated at 0.9.3.

**Caveat**: for the two options probed this way, the change was to what Zuban
*advertises*, not to what it *answers*. With `typeCheckingMode="off"`,
`textDocument/diagnostic` still returned the same diagnostic; with
`disableLanguageServices=true`, hover and completion still returned results. A
client that gates requests on advertised capabilities sees a behavior change;
`Session`, which sends requests unconditionally, does not. The remaining options
(`diagnosticMode`, `pythonExecutable`, `inlayHintMode`) were not probed this way.

---

## Version Information

The September 11, 2026 maintenance used **Zuban 0.9.3**, released September 2.
Fresh temporary LSP sessions reporting that version confirmed:

- The typed `mode="auto"` setting serialized and loaded successfully.
- One virtual document contained assignment errors in four functions. Errors
  were reported in the upper-bounded TypeVar and plain functions, but not in
  either value-constrained TypeVar syntax. Its unnecessary `# type: ignore`
  was not reported either.
- `zuban server --help` lists only `-h/--help`.
- `diagnosticMode="workspace"` changed advertised workspace diagnostics to true;
  `typeCheckingMode="off"` removed the diagnostic provider;
  `disableLanguageServices=true` removed hover and completion providers.
  Nevertheless, direct diagnostic, hover and completion requests still returned
  results with the corresponding advertised services disabled.
- The 18 config tests, including preservation of comments, other sections,
  inline tables and CRLF, passed. This is library behavior verified separately
  from upstream capability claims.

The detailed line-numbered 0.9.2 examples above are historical August 30 evidence.
The newer combined probe reached the same constrained-versus-bounded conclusion.
No fresh behavioral probe was made for `pythonExecutable` or `inlayHintMode`.

Upstream continues to list unused-ignore reporting and constrained generic
bodies under [missing features](https://docs.zubanls.com/en/latest/features.html).
The [0.9.3 changelog](https://docs.zubanls.com/en/latest/changelog.html) records
deterministic file processing and a fix for quadratic literal handling.
