# ty Backend - Known Limitations

This document describes known limitations and behavioral differences when using the ty backend compared to other LSP backends (Pyright, Pyrefly).

## 1. Files Must Exist on Disk

**Limitation**: ty requires Python files to exist on disk before it can provide diagnostics, completion, rename, and other analysis features.

**Behavior**: Opening a "virtual document" via `didOpen` without a corresponding file on disk results in:
- Empty diagnostics (no errors reported even for invalid code)
- Empty or limited completion results
- Rename operations may fail

**Workaround**: Always write files to disk before creating a session:
```python
from pathlib import Path

base_path = Path("/tmp/my_project")
base_path.mkdir(exist_ok=True)

code = "x: int = 'not an int'"
(base_path / "new.py").write_text(code)

session = await Session.create(
    TyBackend(),
    base_path=base_path,
    initial_code=code,
)
diagnostics = await session.get_diagnostics()  # Now returns errors
```

## 2. `workspace/didChangeConfiguration` Not Supported

**Limitation**: ty does not handle the `workspace/didChangeConfiguration` notification.

**Behavior**: ty logs a warning:
```
WARN Received notification workspace/didChangeConfiguration which does not have a handler.
```

**Impact**: Runtime configuration changes via LSP notifications are ignored. However, configuration written to `ty.toml` before session creation is respected.

**Workaround**: Ensure all configuration is set in `ty.toml` via the `options` parameter when creating a session. If configuration needs to change, create a new session.

## 3. Hover Format Differs

**Limitation**: ty's hover information shows only the type, not the variable name.

**Behavior**:
- Pyright/Pyrefly hover: `result: str` or `(variable) result: str`
- ty hover: `str`

**Impact**: Code that parses hover text expecting variable names will not find them with ty.

## 4. No CLI Configuration Flags

**Limitation**: The `ty server` command accepts no configuration flags.

**Behavior**: Unlike Pyrefly which supports `--verbose`, `--threads`, etc., ty's LSP server is configured entirely via `ty.toml`.

**Impact**: No impact on functionality - all configuration works via the config file.

## 5. Workspace Folders Warning

**Limitation**: ty expects `workspaceFolders` in the initialization parameters.

**Behavior**: ty logs a warning when workspaceFolders is not provided:
```
WARN No workspace(s) were provided during initialization. Using the current working directory from the fallback system as a default workspace
```

**Impact**: ty falls back to using the working directory. This typically works correctly but may affect multi-root workspace scenarios.

## 6. File Watching Not Supported by Client

**Limitation**: The current LSP client implementation doesn't support file watching.

**Behavior**: ty logs:
```
WARN Your LSP client doesn't support file watching: You may see stale results when files change outside the editor
```

**Impact**: If files are modified outside the LSP session (e.g., by external tools), ty may not detect the changes until the session is recreated.

---

## Version Information

These limitations were documented based on ty version 0.0.11 (January 2026). Future versions may address some of these limitations.
