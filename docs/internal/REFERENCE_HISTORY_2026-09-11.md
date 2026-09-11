# Archived reference notes — September 11, 2026

Historical documentation preserved during the public-docs cleanup. These notes contain dated observations, superseded wording, and unimplemented proposals; use the public guides for current API guidance.

---

Source: `docs/USAGE.md`

# Usage details

## Low-level stdio

> [!TIP]
> Recommend using [basedpyright](https://github.com/DetachHead/basedpyright) for extended features.

```python
from lsp_types.process import LSPProcess, ProcessLaunchInfo

process_info = ProcessLaunchInfo(cmd=[
    "pyright-langserver", "--stdio"
])

async with LSPProcess(process_info) as process:
    # Initialize the process
    ...

    # Grab a typed listener
    diagnostics_listener = process.notify.on_publish_diagnostics(timeout=1.0)

    # Send a notification (`await` is optional. It ensures messages have been drained)
    await process.notify.did_open_text_document(...)

    # Wait for diagnostics to come in
    diagnostics = await diagnostics_listener
```

`LSPProcess.stop()` is terminal — including the implicit stop() when the `async with`
block exits. Calling `start()` on a stopped process raises `RuntimeError` instead
of relaunching the server, and requests and notifications sent through it raise
`RuntimeError` too (notifications are no longer dropped with a warning). The
messages name the state they came from (`LSP process has been stopped` vs. `LSP
process has not been started`). Construct a new `LSPProcess` when you need to
restart a server.


## Session lifecycle

After `shutdown()`, a session's operational methods raise `RuntimeError`; its
captured server and semantic-token metadata remain readable. Calling
`shutdown()` while other operations are in flight is safe: it waits up to five
seconds for them to finish, and if any are still running it stops the language
server process instead of returning it to the pool, keeping stale operations
out of the next session's protocol stream. (One narrow exception: cancelling
an operation ends its in-flight accounting even if a notification write it
already queued is still being flushed.)


Internal generated types whose names start with `__` are not public API.

---

Source: `docs/SEMANTIC_TOKENS.md`

# Semantic Tokens Reference

This document provides a reference for semantic token types and modifiers returned by each LSP backend. This is particularly useful when integrating with editors like Monaco that need to map token IDs to theme colors.

## Overview

Semantic tokens provide richer syntax highlighting than traditional TextMate grammars by leveraging the language server's understanding of the code. The LSP protocol encodes tokens as a compact integer array where each token is represented by 5 values.

## Token Encoding Format

Each token in the `data` array consists of 5 consecutive integers:

| Position | Field | Description |
|----------|-------|-------------|
| 0 | `deltaLine` | Line offset from previous token (or 0 for first token) |
| 1 | `deltaStart` | Column offset from previous token on same line (or from 0 if new line) |
| 2 | `length` | Token length in characters |
| 3 | `tokenType` | Index into the legend's `tokenTypes` array |
| 4 | `tokenModifiers` | Bitmask of modifiers from the legend's `tokenModifiers` array |

### Decoding Token Modifiers

The `tokenModifiers` value is a bitmask. To check if a modifier applies:

```python
def has_modifier(token_modifiers: int, modifier_index: int) -> bool:
    return (token_modifiers & (1 << modifier_index)) != 0
```

For example, if `tokenModifiers = 5` (binary `101`), modifiers at index 0 and 2 are active.

## How to Get the Legend

The legend is provided by the server during initialization in `InitializeResult.capabilities.semanticTokensProvider.legend`. You can extract it using:

```python
from lsp_types.process import LSPProcess

async with LSPProcess(process_info) as process:
    init_result = await process.send.initialize({...})
    legend = init_result["capabilities"]["semanticTokensProvider"]["legend"]
    token_types = legend["tokenTypes"]      # List of type names
    token_modifiers = legend["tokenModifiers"]  # List of modifier names
```

See `examples/extract_semantic_legends.py` for a complete working example.

---

## Token Legends by Backend

Microsoft Pyright 1.1.414 does **not** provide semantic tokens. The Pyright-family
legend below belongs to the separate basedpyright fork, which uses the same backend.
These are LSP legends, independent of the playground’s WASM APIs.

### basedpyright (through PyrightBackend)

> Last verified: basedpyright 1.40.1 (2026-09-11)

#### Token Types

| Index | Token Type |
|------:|------------|
| 0 | `namespace` |
| 1 | `type` |
| 2 | `class` |
| 3 | `enum` |
| 4 | `typeParameter` |
| 5 | `parameter` |
| 6 | `variable` |
| 7 | `property` |
| 8 | `enumMember` |
| 9 | `function` |
| 10 | `method` |
| 11 | `keyword` |
| 12 | `decorator` |
| 13 | `selfParameter` |
| 14 | `clsParameter` |

#### Token Modifiers

| Bit | Modifier |
|----:|----------|
| 0 | `declaration` |
| 1 | `definition` |
| 2 | `readonly` |
| 3 | `static` |
| 4 | `async` |
| 5 | `defaultLibrary` |
| 6 | `builtin` |
| 7 | `classMember` |
| 8 | `parameter` |

---

### Pyrefly

> Last verified: Pyrefly 1.3.0 (2026-09-11)
> Legend source: [semantic_tokens.rs](https://github.com/facebook/pyrefly/blob/1.3.0/pyrefly/lib/state/semantic_tokens.rs)

Pyrefly does not advertise its legend via LSP initialization, but the token mappings are defined in source code.

#### Token Types

| Index | Token Type |
|------:|------------|
| 0 | `namespace` |
| 1 | `type` |
| 2 | `class` |
| 3 | `enum` |
| 4 | `interface` |
| 5 | `struct` |
| 6 | `typeParameter` |
| 7 | `parameter` |
| 8 | `variable` |
| 9 | `property` |
| 10 | `enumMember` |
| 11 | `event` |
| 12 | `function` |
| 13 | `method` |
| 14 | `macro` |
| 15 | `keyword` |
| 16 | `modifier` |
| 17 | `comment` |
| 18 | `string` |
| 19 | `number` |
| 20 | `regexp` |
| 21 | `operator` |
| 22 | `decorator` |

#### Token Modifiers

| Bit | Modifier |
|----:|----------|
| 0 | `declaration` |
| 1 | `definition` |
| 2 | `readonly` |
| 3 | `static` |
| 4 | `deprecated` |
| 5 | `abstract` |
| 6 | `async` |
| 7 | `modification` |
| 8 | `documentation` |
| 9 | `defaultLibrary` |
| 10 | `selfParameter` |
| 11 | `byteString` |
| 12 | `formatString` |
| 13 | `rawString` |
| 14 | `stringPrefix` |
| 15 | `templateString` |

---

### ty

> Last verified: ty 0.0.80 (2026-09-11)

#### Token Types

| Index | Token Type |
|------:|------------|
| 0 | `namespace` |
| 1 | `class` |
| 2 | `parameter` |
| 3 | `selfParameter` |
| 4 | `clsParameter` |
| 5 | `variable` |
| 6 | `property` |
| 7 | `function` |
| 8 | `method` |
| 9 | `keyword` |
| 10 | `string` |
| 11 | `number` |
| 12 | `decorator` |
| 13 | `builtinConstant` |
| 14 | `typeParameter` |
| 15 | `operator` |
| 16 | `regexp` |

#### Token Modifiers

| Bit | Modifier |
|----:|----------|
| 0 | `definition` |
| 1 | `readonly` |
| 2 | `async` |
| 3 | `documentation` |

---

### Zuban

> Last verified: Zuban 0.9.3 (2026-09-11)

Zuban advertises its legend via LSP initialization (follows LSP 3.17 standard ordering for the 23 token types it emits).

#### Token Types

| Index | Token Type |
|------:|------------|
| 0 | `namespace` |
| 1 | `type` |
| 2 | `class` |
| 3 | `enum` |
| 4 | `interface` |
| 5 | `struct` |
| 6 | `typeParameter` |
| 7 | `parameter` |
| 8 | `variable` |
| 9 | `property` |
| 10 | `enumMember` |
| 11 | `event` |
| 12 | `function` |
| 13 | `method` |
| 14 | `macro` |
| 15 | `keyword` |
| 16 | `modifier` |
| 17 | `comment` |
| 18 | `string` |
| 19 | `number` |
| 20 | `regexp` |
| 21 | `operator` |
| 22 | `decorator` |

#### Token Modifiers

| Bit | Modifier |
|----:|----------|
| 0 | `declaration` |
| 1 | `definition` |
| 2 | `readonly` |
| 3 | `static` |
| 4 | `deprecated` |
| 5 | `abstract` |
| 6 | `async` |
| 7 | `defaultLibrary` |

---

## Monaco Editor Integration

When integrating with Monaco, register a `DocumentSemanticTokensProvider` that:

1. Requests tokens via `session.get_semantic_tokens()`
2. Returns the token data along with the legend

```typescript
// TypeScript example for Monaco
monaco.languages.registerDocumentSemanticTokensProvider('python', {
    getLegend: () => ({
        tokenTypes: ['namespace', 'type', 'class', ...],  // From backend legend
        tokenModifiers: ['declaration', 'definition', ...]
    }),
    provideDocumentSemanticTokens: async (model) => {
        const tokens = await requestSemanticTokens(model.uri);
        return {
            data: new Uint32Array(tokens.data),
            resultId: tokens.resultId
        };
    },
    releaseDocumentSemanticTokens: () => {}
});
```

The token types and modifiers must be registered in the **exact same order** as the backend's legend for the indices to map correctly.

---

## Normalized Semantic Tokens API

The library provides a **normalized tokens API** that remaps token indices to a canonical legend. This allows Monaco/editors to use a single fixed legend regardless of which backend is active.

### The Problem

Each backend has different legend ordering:

| Token | Pyright Index | Pyrefly Index | ty Index | Zuban Index |
|-------|---------------|---------------|----------|-------------|
| `namespace` | 0 | 0 | 0 | 0 |
| `class` | 2 | 2 | 1 | 2 |
| `variable` | 6 | 8 | 5 | 8 |
| `function` | 9 | 12 | 7 | 12 |

A Monaco client configured with one legend breaks when switching backends.

### The Solution

Use the `normalize=True` parameter to get tokens with indices remapped to the canonical legend:

```python
from lsp_types import Session, CANONICAL_LEGEND
from lsp_types.pyright.backend import PyrightBackend

session = await Session.create(PyrightBackend(), initial_code="x = 1")

# Original tokens (backend-specific indices)
raw = await session.get_semantic_tokens()

# Normalized tokens (canonical indices matching CANONICAL_LEGEND)
normalized = await session.get_semantic_tokens(normalize=True)

# Monaco uses one fixed legend for all backends
monaco_legend = CANONICAL_LEGEND
```

### Available Properties

```python
session.canonical_legend   # The canonical legend (fixed, same for all backends)
session.backend_legend     # The original legend from the server/backend
```

### Canonical Legend Order

The canonical legend follows LSP standard ordering, with backend-specific tokens appended:

**Token Types (index 0-26):**
- 0-22: LSP standard types (namespace, type, class, enum, interface, struct, typeParameter, parameter, variable, property, enumMember, event, function, method, macro, keyword, modifier, comment, string, number, regexp, operator, decorator)
- 23: label (LSP standard)
- 24-26: Backend-specific (selfParameter, clsParameter, builtinConstant)

**Token Modifiers (bit 0-18):**
- 0-9: LSP standard modifiers (declaration, definition, readonly, static, deprecated, abstract, async, modification, documentation, defaultLibrary)
- 10-12: Backend-specific from Pyright (builtin, classMember, parameter)
- 13: Backend-specific from Pyrefly (selfParameter)
- 14-18: Pyrefly 1.3 string modifiers (byteString, formatString, rawString, stringPrefix, templateString); appended so existing indices stay stable

---

## Updating This Document

Run the extraction script to get the latest legends:

```bash
uv run python examples/extract_semantic_legends.py
```

Update the tables above with the script output when backend versions change.

---

Source: `docs/INTEGRATION_NOTES.md`

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

**Current artifact check (2026-09-11):** installed `monaco-editor` is still
0.56.0. The public declaration still exposes only `constructor(transport)` and
no `dispose()`; the shipped LSP client hardcodes `rootUri: null`, omits
`initializationOptions`, and discards the feature disposable store. The two
migration blockers below remain. The playground's existing adapters were built
and smoke-tested in Chromium; the other issue statuses below are historical,
not freshly verified.

**Blockers / caveats (re-verified against v0.56.0 — 2026-08-30):**

The August 30 verification was documentary only: npm was unavailable on that
machine, so nothing was installed or executed in that earlier run. Evidence came from the published npm artifacts (`monaco.d.ts`
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

---

Source: `lsp_types/pyrefly/KNOWN_LIMITATIONS.md`

# Pyrefly backend: known limitations

Verified with **Pyrefly 1.3.0 on 2026-09-11** using this library's LSP client.
Release notes are dated September 10; PyPI and GitHub publication occurred
September 11 UTC. [Release](https://github.com/facebook/pyrefly/releases/tag/1.3.0)

## Completion resolution is an echo

`completionItem/resolve` returns the submitted item unchanged, despite
advertising `completionProvider.resolveProvider: true`. A live probe resolved
a method completion both normally and with `detail`/`documentation` removed;
both responses exactly matched their respective inputs.

Initial completions already include type details and documentation, so ordinary
completion remains useful. Calling `resolve_completion()` succeeds but does
not retrieve additional metadata.

## Semantic-token legend is not advertised

The initialize response omits `semanticTokensProvider` entirely, while
`textDocument/semanticTokens/full` still returns tokens. The backend therefore
supplies `PYREFLY_LEGEND` instead of discovering a legend from the server.

Pyrefly 1.3.0 adds five string modifiers: `byteString`, `formatString`,
`rawString`, `stringPrefix`, and `templateString` (bits 11–15). This maintenance
updates both the fallback legend and canonical modifiers so normalization
preserves those bits. Token types are unchanged. See
[semantic-token documentation](../SEMANTIC_TOKENS.md).

## Configuration and API boundaries

The backend writes kebab-case TOML keys from top-level snake_case Python keys.
Nested error-code keys should use the upstream names (`bad-assignment`, etc.).
The typed schema covers common options; a plain `Session.create(options=...)`
dictionary can carry other upstream settings.

Upstream CLI tools, TSP, and editor refactorings extend beyond the high-level
`Session` API. Their availability upstream does not imply a matching Session
method. Tensor-shape and DataFrame schema extensions remain experimental.

## Previously resolved

Rename previously failed for session files classified as external. It has
worked since 1.1.1 and remains covered by the regular rename integration test;
the former expected failure is gone. Virtual documents work without on-disk
mirroring.

---

Source: `lsp_types/ty/KNOWN_LIMITATIONS.md`

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

---

Source: `lsp_types/zuban/KNOWN_LIMITATIONS.md`

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
