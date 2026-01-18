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

### Pyright (basedpyright)

> Last verified: basedpyright 1.36.2

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

> Last verified: Pyrefly 0.48.2
> Legend source: [semantic_tokens.rs](https://github.com/facebook/pyrefly/blob/main/pyrefly/lib/state/semantic_tokens.rs)

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

---

### ty

> Last verified: ty 0.0.12

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

#### Token Modifiers

| Bit | Modifier |
|----:|----------|
| 0 | `definition` |
| 1 | `readonly` |
| 2 | `async` |
| 3 | `documentation` |

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

## Updating This Document

Run the extraction script to get the latest legends:

```bash
uv run python examples/extract_semantic_legends.py
```

Update the tables above with the script output when backend versions change.
