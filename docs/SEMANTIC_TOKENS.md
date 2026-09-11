# 🎨 Semantic tokens

Semantic tokens give editors type-aware syntax highlighting. basedpyright,
Pyrefly, ty, and Zuban support them; Microsoft Pyright does not.

## Normalized Semantic Tokens API

Use `normalize=True` with `CANONICAL_LEGEND` to keep editor colors consistent
when switching backends. Raw indexes differ:

| Token | basedpyright Index | Pyrefly Index | ty Index | Zuban Index |
|-------|---------------|---------------|----------|-------------|
| `namespace` | 0 | 0 | 0 | 0 |
| `class` | 2 | 2 | 1 | 2 |
| `variable` | 6 | 8 | 5 | 8 |
| `function` | 9 | 12 | 7 | 12 |

Request normalized tokens and send `CANONICAL_LEGEND` to the editor:

```python
from pathlib import Path
from tempfile import TemporaryDirectory

from lsp_types import CANONICAL_LEGEND, Session
from lsp_types.ty import TyBackend

with TemporaryDirectory() as workspace:
    session = await Session.create(
        TyBackend(), base_path=Path(workspace), initial_code="x = 1"
    )
    try:
        tokens = await session.get_semantic_tokens(normalize=True)
        legend = CANONICAL_LEGEND
    finally:
        await session.shutdown()
```

Run this code inside an async function. It requires the ty extra
(`uv add "lsp-types[ty]"`).

Normalization requires a backend legend. If no legend is available, the method
returns raw tokens unchanged; unsupported servers still reject the request.

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
- 10-12: Backend-specific from basedpyright (builtin, classMember, parameter)
- 13: Backend-specific from Pyrefly (selfParameter)
- 14-18: Pyrefly string modifiers (byteString, formatString, rawString, stringPrefix, templateString)

## Token Encoding Format

Each token in the `data` array consists of 5 consecutive integers:

| Position | Field | Description |
|----------|-------|-------------|
| 0 | `deltaLine` | Line offset from previous token (from line 0 for the first token) |
| 1 | `deltaStart` | Column offset from previous token on same line (or from 0 if new line) |
| 2 | `length` | Token length in the negotiated position encoding |
| 3 | `tokenType` | Index into the legend's `tokenTypes` array |
| 4 | `tokenModifiers` | Bitmask of modifiers from the legend's `tokenModifiers` array |

### Decoding Token Modifiers

The `tokenModifiers` value is a bitmask. To check if a modifier applies:

```python
def has_modifier(token_modifiers: int, modifier_index: int) -> bool:
    return (token_modifiers & (1 << modifier_index)) != 0
```

For example, if `tokenModifiers = 5` (binary `101`), modifiers at index 0 and 2 are active.

## Backend legend

`session.backend_legend` contains the server's legend or the backend's fallback.
For low-level clients, read
`InitializeResult.capabilities.semanticTokensProvider.legend` when present.
Pyrefly omits this capability; use `PYREFLY_LEGEND` from
`lsp_types.semantic_tokens` for its raw tokens.

## Token Legends by Backend

The tables below describe each server’s raw LSP indexes. Read
`session.backend_legend` for the running server’s ordering. These legends apply
to LSP sessions; browser WASM APIs have their own feature sets.

### basedpyright 1.40.1 (through PyrightBackend)

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

### Pyrefly 1.3.0

Legend source: [semantic_tokens.rs](https://github.com/facebook/pyrefly/blob/1.3.0/pyrefly/lib/state/semantic_tokens.rs)

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

### ty 0.0.80

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

### Zuban 0.9.3

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

Register a `DocumentSemanticTokensProvider` with the legend paired to your
Python response. In this example, `canonicalLegend` is the JSON representation
of `CANONICAL_LEGEND`, and `requestSemanticTokens` calls
`session.get_semantic_tokens(normalize=True)` through your application’s transport.

```typescript
// TypeScript example for Monaco
monaco.languages.registerDocumentSemanticTokensProvider('python', {
    getLegend: () => canonicalLegend,
    provideDocumentSemanticTokens: async (model) => {
        const tokens = await requestSemanticTokens(model.uri);
        if (!tokens) return null;
        return {
            data: new Uint32Array(tokens.data),
            resultId: tokens.resultId
        };
    },
    releaseDocumentSemanticTokens: () => {}
});
```

Match the legend to the data: use `CANONICAL_LEGEND` for normalized tokens and
`session.backend_legend` for raw tokens. Preserve the legend’s exact ordering.
