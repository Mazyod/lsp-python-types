# ty Backend - Known Limitations

This document describes known limitations and behavioral differences when using the ty backend compared to other LSP backends (Pyright, Pyrefly).

## 1. `workspace/didChangeConfiguration` Not Supported

**Limitation**: ty does not handle the `workspace/didChangeConfiguration` notification.

**Behavior**: ty would log a warning if the notification were sent:
```
WARN Received notification workspace/didChangeConfiguration which does not have a handler.
```

**Impact**: Runtime configuration changes via LSP notifications are ignored. However, configuration written to `ty.toml` before session creation is respected.

**Resolution**: `TyBackend` implements `consumes_did_change_configuration() -> False`,
so `Session.create()` skips the notification entirely — the warning above no longer
appears in stderr. This remains the right call: the notification is genuinely
unhandled, so sending it produces a warning and no effect.

Configuration does not have to live in `ty.toml`, however. ty also reads
`initializationOptions.configuration` at initialization, which accepts inline ty
config using kebab-case keys (`{"configuration": {"rules": {"unresolved-import":
"ignore"}}}` was verified to suppress that diagnostic with no `ty.toml` present;
the snake_case spelling is silently ignored). Pass it through the public
`Session.create(..., initialize_params={"initializationOptions": {...}})`
parameter. This mirrors Zuban, which honors its own `initializationOptions` —
several backends in this repo accept LSP-time configuration, so "file-based only"
is the wrong mental model. What remains true for ty is that configuration cannot
be changed *after* the session starts: to change it, create a new session.

## 2. Hover Format Differs

**Limitation**: ty's hover information shows only the type, not the variable name.

**Behavior**:
- Pyright/Pyrefly hover: `result: str` or `(variable) result: str`
- ty hover: `str`

**Impact**: Code that parses hover text expecting variable names will not find them with ty.

## 3. No CLI Configuration Flags

**Limitation**: The `ty server` command accepts no configuration flags.

**Behavior**: Unlike Pyrefly which supports `--verbose`, `--threads`, etc.,
`ty server --help` lists only `-h, --help`.

**Impact**: None on functionality. Configuration reaches ty through two channels
rather than the command line: `ty.toml` (what `TyBackend.write_config()` writes),
and `initializationOptions` at LSP initialization — see limitation 1. Two keys
were verified to have a real effect there: `logLevel` (changes server log
verbosity) and `configuration` (applies inline ty config). Others are accepted
without a warning, but their effect was not confirmed and should not be assumed:
`diagnosticMode`, `disableLanguageServices`, `configuration-file`, `inlayHints`,
`completions`, `pythonExtension`, `workspaceTrust`, `experimental`,
`showSyntaxErrors`.

ty warns loudly on unrecognized *top-level* initialization-option keys, so a typo
there is visible. That does not extend to nested keys: a misspelled rule name
inside `configuration` is silently ignored, as limitation 1 records for the
snake_case spelling of `unresolved-import`.

## 4. Workspace Folders Warning

**Limitation**: ty expects `workspaceFolders` in the initialization parameters.

**Behavior**: ty logs a warning when workspaceFolders is not provided:
```
WARN No workspace(s) were provided during initialization. Using the current working directory from the fallback system as a default workspace
```

**Impact**: ty falls back to using the working directory. This typically works correctly but may affect multi-root workspace scenarios.

## 5. File Watching Not Supported by Client

**Limitation**: This library's LSP client does not implement file watching, and ty
adjusts its warning to how much watching the client claims to support.

**Behavior**: With the capabilities `TyBackend` currently advertises, ty logs:
```
WARN Your LSP client doesn't support file watching: You may see stale results when files change outside the editor
```
Advertising `workspace.didChangeWatchedFiles.dynamicRegistration` narrows this to
"...doesn't support file watching **outside of project**: You may see stale results
when **dependencies change**". Additionally advertising `relativePatternSupport`
removes the warning entirely. This tiering is not new — it behaves identically at
ty 0.0.70.

**Why the warning is left in place**: silencing it by advertising those
capabilities would be dishonest, not a fix. When `dynamicRegistration` is
advertised, ty replies with a `client/registerCapability` *request*, and this
client cannot answer it: the read loop tests `if "method" in payload` before
`elif "id" in payload` (`lsp_types/process.py:480`), so a server-initiated
request — which carries both — is routed to the notification listeners and never
answered. Advertising a capability we do not implement and then leaving ty's
request hanging is worse than the warning. A real fix needs server-request
replies plus actual file watching.

**Impact**: Files modified outside the LSP session (by external tools, a build
step, or a dependency install) may not be picked up until the session is
recreated. Sessions that only ever mutate the document through `update_code()`
are unaffected.

## 6. Completion Item Resolution Not Supported

**Limitation**: ty does not support the `completionItem/resolve` LSP request.

**Behavior**: Calling `resolve_completion()` will raise an error:
```
Unknown request: completionItem/resolve (-32601)
```

**Impact**: Completion items won't have extended documentation or additional metadata that resolution typically provides. Basic completion works fine.

---

## Previously Documented, Now Resolved

- **Files must exist on disk** (documented for ty 0.0.11): Early ty versions returned empty diagnostics, limited completions, and failing renames for "virtual documents" opened via `didOpen` without a corresponding file on disk, so `TyBackend` mirrored the session code to disk (`requires_file_on_disk() -> True`). Bisecting PyPI releases shows virtual documents work from ty 0.0.16 onward (diagnostics on `didOpen` and `didChange`, completion, and rename all verified with no `.py` file on disk). The backend no longer writes files to disk, and the package floor is now `ty>=0.0.16`.

---

## Version Information

These limitations were documented based on ty version 0.0.11 (January 2026), last
verified with ty 0.0.75 (August 30, 2026), which is the newest release on PyPI.

All six entries were probed directly against 0.0.75, each with a control case
proving the probe could detect the opposite result. **None of the six was fixed.**
The identical probe suite was then re-run against a pinned ty 0.0.70 in a throwaway
virtualenv: behaviour was byte-identical on all six. Nothing regressed and nothing
was fixed in 0.0.70..0.0.75, and the release notes for 0.0.71-0.0.75 contain no LSP
change bearing on these entries. The `ty>=0.0.16` floor in `pyproject.toml` remains
correct.

Two entries read differently than their original wording suggests:

- Limitation 4 is a gap in *this client*, not in ty. Supplying `workspaceFolders`
  in the initialize params (URI matching `base_path`) removes the warning with no
  loss of function: diagnostics stay correct and `ty.toml` is still applied.
  `Session.create()` does not currently send the field. A folder URI that is not a
  real directory is worse than sending none — ty falls back to default settings and
  reports no diagnostics at all.
- Limitation 5 is tiered by client capability and should be left alone; see that
  section for why silencing it would be a regression in honesty, not a fix.

Limitation 1 is narrower than originally written: the notification is still
unhandled, but ty does accept configuration over LSP at initialization via
`initializationOptions`. Configuration still cannot be changed after a session
starts.

Future versions may address some of these limitations.
