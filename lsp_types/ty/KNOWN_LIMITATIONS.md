# ty Backend - Known Limitations

This document describes known limitations and behavioral differences when using the ty backend compared to other LSP backends (Pyright, Pyrefly).

## 1. `workspace/didChangeConfiguration` Not Supported

**Limitation**: ty does not handle the `workspace/didChangeConfiguration` notification.

**Behavior**: ty would log a warning if the notification were sent:
```
WARN Received notification workspace/didChangeConfiguration which does not have a handler.
```

**Impact**: Runtime configuration changes via LSP notifications are ignored. However, configuration written to `ty.toml` before session creation is respected.

**Resolution**: `TyBackend` implements `consumes_did_change_configuration() -> False`, so `Session.create()` skips the notification entirely — the warning above no longer appears in stderr. All configuration must still be set in `ty.toml` via the `options` parameter when creating a session; to change configuration at runtime, create a new session.

## 2. Hover Format Differs

**Limitation**: ty's hover information shows only the type, not the variable name.

**Behavior**:
- Pyright/Pyrefly hover: `result: str` or `(variable) result: str`
- ty hover: `str`

**Impact**: Code that parses hover text expecting variable names will not find them with ty.

## 3. No CLI Configuration Flags

**Limitation**: The `ty server` command accepts no configuration flags.

**Behavior**: Unlike Pyrefly which supports `--verbose`, `--threads`, etc., ty's LSP server is configured entirely via `ty.toml`.

**Impact**: No impact on functionality - all configuration works via the config file.

## 4. Workspace Folders Warning

**Limitation**: ty expects `workspaceFolders` in the initialization parameters.

**Behavior**: ty logs a warning when workspaceFolders is not provided:
```
WARN No workspace(s) were provided during initialization. Using the current working directory from the fallback system as a default workspace
```

**Impact**: ty falls back to using the working directory. This typically works correctly but may affect multi-root workspace scenarios.

## 5. File Watching Not Supported by Client

**Limitation**: The current LSP client implementation doesn't support file watching.

**Behavior**: ty logs:
```
WARN Your LSP client doesn't support file watching: You may see stale results when files change outside the editor
```

**Impact**: If files are modified outside the LSP session (e.g., by external tools), ty may not detect the changes until the session is recreated.

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

These limitations were documented based on ty version 0.0.11 (January 2026), last verified with ty 0.0.70 (August 2026). Hover-shows-type-only and `completionItem/resolve` returning `-32601` were both re-confirmed against 0.0.70. Future versions may address some of these limitations.
