# LSP Backend Integration Notes

This document captures frictions and enhancement opportunities discovered while integrating new LSP backends into lsp-python-types.

## ty Backend Integration (January 2026)

### Frictions Encountered

#### 1. Virtual Document Support

**Issue**: ty requires files to exist on disk before it can provide diagnostics, completion, and other features. Pyright and Pyrefly work with "virtual documents" opened via `didOpen` without requiring the file to exist on disk.

**Impact**: Tests that don't write files to disk fail for ty. The following parametrized tests required `xfail` markers for ty:
- `test_session_diagnostics`
- `test_session_rename`
- `test_session_completion`
- `test_session_recycling_with_diagnostics`
- `test_session_warmup_on_recycle` (in test_pool.py)

**Workaround**: ty-specific tests must write files to disk using `tmp_path`:
```python
(tmp_path / "new.py").write_text(code)
session = await Session.create(backend, base_path=tmp_path, initial_code=code)
```

**Potential Enhancement**: Consider adding a `requires_file_on_disk` property to the `LSPBackend` protocol, allowing the Session class to automatically write files when needed.

#### 2. `workspace/didChangeConfiguration` Not Supported

**Issue**: ty logs `Received notification workspace/didChangeConfiguration which does not have a handler.` The Session class sends this notification after initialization to apply workspace settings.

**Impact**: Runtime configuration changes via `didChangeConfiguration` don't work with ty. However, configuration written to `ty.toml` is respected.

**Current Behavior**: The notification is sent but ignored by ty. No functional impact since config file is written first.

**Potential Enhancement**: Add an optional `supports_did_change_configuration` flag to backends so the Session can skip sending this notification when unsupported.

#### 3. Nested Configuration Structure

**Issue**: ty uses nested TOML sections (`[environment]`, `[src]`, `[rules]`) unlike Pyrefly's flat structure. This required implementing recursive key conversion.

**Solution**: Created `_convert_keys_to_kebab()` function in `lsp_types/ty/backend.py`:
```python
def _convert_keys_to_kebab(obj: t.Mapping[str, t.Any]) -> dict[str, t.Any]:
    """Recursively convert dict keys from snake_case to kebab-case."""
    result: dict[str, t.Any] = {}
    for key, value in obj.items():
        kebab_key = key.replace("_", "-")
        if isinstance(value, dict):
            result[kebab_key] = _convert_keys_to_kebab(value)
        elif isinstance(value, list):
            result[kebab_key] = [
                _convert_keys_to_kebab(v) if isinstance(v, dict) else v
                for v in value
            ]
        else:
            result[kebab_key] = value
    return result
```

**Potential Enhancement**: Extract this utility to a shared module (`lsp_types/utils.py`) since Pyrefly also uses TOML with kebab-case keys (though currently with flat structure).

#### 4. Hover Information Format Differences

**Issue**: ty's hover response shows just the type (`str`) rather than `variable_name: type` format used by Pyright and Pyrefly.

**Impact**: Test assertions checking for variable names in hover text fail for ty.

**Workaround**: Added backend-specific assertion in `test_session_hover`:
```python
if backend_name != "ty":
    assert "result" in hover_text
assert "str" in hover_text
```

#### 5. No CLI Flags for LSP Server

**Issue**: Unlike Pyrefly which accepts `--verbose`, `--threads`, and `--indexing-mode` CLI flags, ty's `server` command accepts no configuration flags.

**Impact**: All configuration must be done via `ty.toml`. This is actually simpler than Pyrefly's hybrid approach.

**Solution**: `create_process_launch_info()` simply returns `["ty", "server"]` without any conditional flag building.

---

## Enhancement Opportunities

### 1. Shared TOML Key Conversion Utility

Both Pyrefly and ty use TOML with kebab-case keys but Python code uses snake_case. Consider creating:

```python
# lsp_types/utils.py
def snake_to_kebab_recursive(obj: Mapping[str, Any]) -> dict[str, Any]:
    """Recursively convert dict keys from snake_case to kebab-case."""
    # ... implementation
```

Then refactor both backends to use this shared utility.

### 2. Backend Capability Flags

Add optional flags to the `LSPBackend` protocol for:
- `requires_file_on_disk: bool` - Whether backend needs files to exist on disk
- `supports_did_change_configuration: bool` - Whether backend handles `workspace/didChangeConfiguration`

This would allow the Session class to adapt its behavior automatically.

### 3. Common LSP Capabilities Base

Create a helper function for shared capabilities:

```python
def get_base_python_capabilities() -> types.ClientCapabilities:
    """Common LSP capabilities for Python type checkers."""
    return {
        "textDocument": {
            "publishDiagnostics": {...},
            "hover": {...},
            "signatureHelp": {},
        }
    }
```

Backends could extend this base instead of duplicating the boilerplate.

### 4. Backend Registry Pattern

For easier discovery and testing:

```python
_BACKENDS: dict[str, type[LSPBackend]] = {}

def register_backend(name: str):
    def decorator(cls):
        _BACKENDS[name] = cls
        return cls
    return decorator

@register_backend("ty")
class TyBackend(LSPBackend):
    ...
```

---

## Summary

The ty backend integration revealed that different LSP servers have varying requirements around file handling and configuration. The current abstraction works but could benefit from:

1. Optional capability flags on backends
2. Shared utilities for common patterns (TOML conversion, base capabilities)
3. Better documentation of backend-specific behaviors

The core `LSPBackend` protocol and `Session` class work well across all three backends (Pyright, Pyrefly, ty) with minimal backend-specific handling needed in tests.
