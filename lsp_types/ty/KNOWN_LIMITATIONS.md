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
"ignore"}}}` was verified to suppress that diagnostic with an empty `ty.toml`;
the snake_case spelling is silently ignored). Pass it through the public
`Session.create(..., initialize_params={"initializationOptions": {...}})`
parameter. This mirrors Zuban, which honors its own `initializationOptions` —
several backends in this repo accept LSP-time configuration, so "file-based only"
is the wrong mental model. This integration applies configuration when creating
the session. Recreate the session to change it reliably; its default null
configuration replies and lack of file watching do not provide settings updates.

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
and `initializationOptions` at LSP initialization — see limitation 1. The August
30 probe verified two keys with a real effect: `logLevel` (changes server log
verbosity) and `configuration` (applies inline ty config). Others are accepted
without a warning, but their effect was not confirmed and should not be assumed:
`diagnosticMode`, `disableLanguageServices`, `inlayHints`,
`completions`, `pythonExtension`, `workspaceTrust`, `experimental`,
`showSyntaxErrors`. The current documented setting for an explicit TOML path is
`configurationFile`; the older probe used `configuration-file` and did not
establish its behavior. See the [editor settings reference](https://docs.astral.sh/ty/reference/editor-settings/).

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
**Historical probe (0.0.70 and 0.0.75, August 30):** Advertising
`workspace.didChangeWatchedFiles.dynamicRegistration` narrowed the warning to
watching outside the project; also advertising `relativePatternSupport` removed
it. These capability variants were not rerun in the September maintenance.

**Why the warning is left in place:** this library has no file watchers. The
process now answers server requests: its default handler returns null
configuration entries, acknowledges registration requests, and replies
`-32601` for unknown methods. That prevents protocol stalls, but acknowledging a
registration does not install a watcher. Advertising watching support would
still promise behavior this client does not provide.

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

**Impact**: Clients must use the initial completion response; they cannot fetch
additional details through a separate resolution request. Basic completion works.

---

## Previously Documented, Now Resolved

- **Files must exist on disk** (documented for ty 0.0.11): Early ty versions returned empty diagnostics, limited completions, and failing renames for "virtual documents" opened via `didOpen` without a corresponding file on disk, so `TyBackend` mirrored the session code to disk (`requires_file_on_disk() -> True`). Bisecting PyPI releases shows virtual documents work from ty 0.0.16 onward (diagnostics on `didOpen` and `didChange`, completion, and rename all verified with no `.py` file on disk). The backend no longer writes files to disk, and the package floor is now `ty>=0.0.16`.

---

## Version Information

The September 11, 2026 maintenance used **ty 0.0.80**. Fresh temporary
LSP sessions confirmed:

- `workspace/didChangeConfiguration` still logs an unhandled-notification
  warning. An unresolved import remained after sending a suppressing setting
  and editing the document; inline initialization with the correct kebab-case
  rule suppressed it, while an unrelated assignment error remained. The
  snake_case rule spelling did not suppress it.
- Hover over `result: str = "ok"` returned `Literal["ok"]`, without its name.
- `ty server --help` lists only `-h/--help`.
- The default initialization emits both missing-workspace and missing-watcher
  warnings. Supplying a valid `workspaceFolders` removed the former while
  retaining correct diagnostics. Session does not currently supply this field.
- Resolving a real completion item returned `-32601`.
- All diagnostic and hover probes used virtual documents, with no `.py` file on
  disk. New analysis configuration serialized and loaded successfully; an
  `allowed_unresolved_imports` entry suppressed its matching unresolved import
  without suppressing the assignment control.

Historical August 30 probes compared 0.0.70 and 0.0.75 and found identical behavior
for the six entries. That run also checked log-level changes, invalid workspace
paths and watcher-capability variants. Those details remain historical evidence,
not claims that every variant was repeated at 0.0.80.
