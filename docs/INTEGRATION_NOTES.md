# LSP Backend Integration Notes

This document captures frictions and enhancement opportunities discovered while integrating new LSP backends into lsp-python-types.

## ty Backend Integration (January 2026)

### Frictions Encountered

#### 1. Virtual Document Support (Resolved)

**Issue**: ty (as integrated at 0.0.11) required files to exist on disk before it could provide diagnostics, completion, and other features. Pyright and Pyrefly work with "virtual documents" opened via `didOpen` without requiring the file to exist on disk.

**Original workaround**: The `requires_file_on_disk()` flag was added to the `LSPBackend` protocol so `Session.create()`/`update_code()` could mirror the session code to disk for ty.

**Resolution (August 2026)**: Bisecting PyPI releases showed ty supports virtual documents from 0.0.16 onward (diagnostics, completion, and rename all verified with no file on disk). `TyBackend.requires_file_on_disk()` now returns `False` and the package floor is `ty>=0.0.16`. The protocol flag remains for any future backend that needs it.

#### 2. `workspace/didChangeConfiguration` Not Supported

**Issue**: ty logs `Received notification workspace/didChangeConfiguration which does not have a handler.` The Session class sends this notification after initialization to apply workspace settings, unless the backend opts out.

**Impact**: Runtime configuration changes via `didChangeConfiguration` don't work with ty. However, configuration written to `ty.toml` is respected.

**Resolution**: The `LSPBackend` protocol gained `consumes_did_change_configuration()` (default `True`). `TyBackend` and `ZubanBackend` return `False`, so `Session.create()` skips the notification entirely for them. No functional loss — both read their config from disk.

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

**Impact**: Configuration reaches ty via `ty.toml` or via `initializationOptions` at
LSP initialization, not via the command line. See ty's KNOWN_LIMITATIONS entries 1 and 3.

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

### 2. Backend Capability Flags (implemented)

The `LSPBackend` protocol carries both as methods:
- `requires_file_on_disk() -> bool` — all four backends return `False`
- `consumes_did_change_configuration() -> bool` — `False` for ty and Zuban

`Session.create()` branches on both.

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

### 4. Monaco Native LSP Client (`monaco.lsp`)

Monaco Editor v0.55.0 (November 2025) introduced a built-in LSP client under `monaco.lsp` that could significantly simplify the playground. The current playground manually handles JSON-RPC, the LSP handshake, position conversion, diagnostics, and hover registration (~200 lines per backend). With `monaco.lsp`, this reduces to ~10-15 lines per backend.

**What it provides:**
- `MonacoLspClient` — auto-registers 21 LSP features (completion, hover, diagnostics, semantic tokens, go-to-definition, rename, code actions, inlay hints, etc.)
- `WebSocketTransport` — connect via WebSocket
- `createTransportToWorker(worker)` — connect to a Web Worker
- `createTransportToIFrame(iframe)` — connect to an iframe

**Example usage:**
```typescript
const worker = new Worker(PYRIGHT_WORKER_URL);
const transport = monaco.lsp.createTransportToWorker(worker);
new monaco.lsp.MonacoLspClient(transport);
// All features auto-registered, including semantic tokens
```

**What it would replace in the playground:**
- `BackendAdapter` interface (diagnostics, hover, updateCode)
- `typeConversions.ts` (LSP-to-Monaco position mapping)
- Per-backend implementations (~200 lines each)
- Dependencies: `vscode-languageserver-protocol`, `vscode-jsonrpc`

**Blockers / caveats (re-verified against v0.56.0 — 2026-08-30):**

Verification was documentary only: there is no npm on the machine, so nothing was
installed or executed. Evidence came from the published npm artifacts (`monaco.d.ts`
and the shipped `esm/external/monaco-lsp-client/out/index.js` for 0.55.1 and 0.56.0,
fetched via CDN), the `monaco-lsp-client/` source at `main`, and the issue trackers.
The decisive check: diffing the shipped LSP bundle 0.55.1 -> 0.56.0 yields 50 lines —
untrusted markdown, a stray `debugger;` removal, one import rename. The client is
functionally unchanged, so every blocker below still stands.

- **API still unstable** — `monaco-lsp-client/README.md` (current): "This package is
  in alpha stage and might contain many bugs." 0.56.0 added typings (0.55.1 shipped
  no `.d.ts` at all) but made no stability declaration.
- **No custom initialization params — still the main blocker.**
  `constructor(transport: IMessageTransport)` is the entire public API; the client
  hardcodes `{ processId: null, capabilities, rootUri: null }` and never sends
  `initializationOptions`. Identical in 0.55.1, 0.56.0 and `main`.
- **Registration is global in practice for our backends** (the original wording was
  too broad). Providers register against
  `toMonacoLanguageSelector(capability.documentSelector)`, which falls back to
  `{ language: "*" }` only when that selector is missing or empty — so capabilities
  registered dynamically via `client/registerCapability` *are* scoped per-language.
  But options derived from static server capabilities carry no document selector,
  and Pyright, Pyrefly, ty and Zuban all advertise statically.
- **No reconnection** — `WebSocketTransport`'s `socket.onclose` only flips transport
  state to `closed`; nothing subscribes to that state, and `reconnect` appears zero
  times in the shipped bundle.
- **No `dispose()`** (microsoft/monaco-editor#5340, open) — new since this note was
  written, and disqualifying on its own here. `createFeatures()` builds a
  `DisposableStore` that the constructor discards, and `MonacoLspClient` exposes no
  `dispose()`, so provider registrations outlive the transport for the page lifetime.
  `playground/src/main.ts` disposes the adapter on every backend switch, so each
  switch would leak a full set of providers.
- **Other open bugs to watch** — microsoft/monaco-editor#5224 and #5239 (document
  URIs are case-mangled during text-document synchronisation) and #5342
  (`textDocument/codeAction` drops the diagnostic `data`, `code` and `source` fields
  servers need for quickfixes).

**Recommendation:** Do not migrate on monaco-editor 0.56.0. Re-evaluate only once
both a `MonacoLspClient` constructor accepting initialization options and a proper
`dispose()` have landed; #5340 is a required lifecycle fix, not merely something to
monitor. Treat 0.57+ as a release horizon to re-check, not an expectation that it
will be usable. If both land, migrating the playground would eliminate significant
boilerplate and gain features (completion, semantic tokens, rename, etc.) for free.

### 5. Backend Registry Pattern

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

The ty backend integration revealed that different LSP servers have varying requirements around file handling and configuration. Optional capability flags on backends have since shipped (`requires_file_on_disk()`, `consumes_did_change_configuration()`). The current abstraction works but could still benefit from:

1. Shared utilities for common patterns (TOML conversion, base capabilities)
2. Better documentation of backend-specific behaviors

The core `LSPBackend` protocol and `Session` class work well across all four backends (Pyright, Pyrefly, ty, Zuban) with minimal backend-specific handling needed in tests.
