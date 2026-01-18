"""Canonical semantic token legend and normalization utilities."""

from __future__ import annotations

from . import types

# Canonical token types (LSP standard order, then backend-specific)
CANONICAL_TOKEN_TYPES: list[str] = [
    # LSP standard (SemanticTokenTypes enum order)
    "namespace",  # 0
    "type",  # 1
    "class",  # 2
    "enum",  # 3
    "interface",  # 4
    "struct",  # 5
    "typeParameter",  # 6
    "parameter",  # 7
    "variable",  # 8
    "property",  # 9
    "enumMember",  # 10
    "event",  # 11
    "function",  # 12
    "method",  # 13
    "macro",  # 14
    "keyword",  # 15
    "modifier",  # 16
    "comment",  # 17
    "string",  # 18
    "number",  # 19
    "regexp",  # 20
    "operator",  # 21
    "decorator",  # 22
    "label",  # 23 (LSP standard)
    # Backend-specific (appended)
    "selfParameter",  # 24 (pyright, ty)
    "clsParameter",  # 25 (pyright, ty)
    "builtinConstant",  # 26 (ty)
]

# Canonical token modifiers (LSP standard order, then backend-specific)
CANONICAL_TOKEN_MODIFIERS: list[str] = [
    # LSP standard (SemanticTokenModifiers enum order)
    "declaration",  # bit 0
    "definition",  # bit 1
    "readonly",  # bit 2
    "static",  # bit 3
    "deprecated",  # bit 4
    "abstract",  # bit 5
    "async",  # bit 6
    "modification",  # bit 7
    "documentation",  # bit 8
    "defaultLibrary",  # bit 9
    # Backend-specific (appended)
    "builtin",  # bit 10 (pyright)
    "classMember",  # bit 11 (pyright)
    "parameter",  # bit 12 (pyright - modifier, not to be confused with type)
]

# The canonical legend for Monaco/editor integration
CANONICAL_LEGEND: types.SemanticTokensLegend = {
    "tokenTypes": CANONICAL_TOKEN_TYPES,
    "tokenModifiers": CANONICAL_TOKEN_MODIFIERS,
}

# Build lookup tables for canonical indices
_CANONICAL_TYPE_INDEX: dict[str, int] = {
    name: idx for idx, name in enumerate(CANONICAL_TOKEN_TYPES)
}
_CANONICAL_MODIFIER_INDEX: dict[str, int] = {
    name: idx for idx, name in enumerate(CANONICAL_TOKEN_MODIFIERS)
}

# Pyrefly legend (server doesn't advertise it via LSP)
# Source: https://github.com/facebook/pyrefly/blob/main/pyrefly/lib/state/semantic_tokens.rs
PYREFLY_LEGEND: types.SemanticTokensLegend = {
    "tokenTypes": [
        "namespace",  # 0
        "type",  # 1
        "class",  # 2
        "enum",  # 3
        "interface",  # 4
        "struct",  # 5
        "typeParameter",  # 6
        "parameter",  # 7
        "variable",  # 8
        "property",  # 9
        "enumMember",  # 10
        "event",  # 11
        "function",  # 12
        "method",  # 13
        "macro",  # 14
        "keyword",  # 15
        "modifier",  # 16
        "comment",  # 17
        "string",  # 18
        "number",  # 19
        "regexp",  # 20
        "operator",  # 21
        "decorator",  # 22
    ],
    "tokenModifiers": [
        "declaration",  # bit 0
        "definition",  # bit 1
        "readonly",  # bit 2
        "static",  # bit 3
        "deprecated",  # bit 4
        "abstract",  # bit 5
        "async",  # bit 6
        "modification",  # bit 7
        "documentation",  # bit 8
        "defaultLibrary",  # bit 9
    ],
}


def build_type_mapping(backend_legend: types.SemanticTokensLegend) -> dict[int, int]:
    """Build mapping from backend token type indices to canonical indices."""
    mapping: dict[int, int] = {}
    for backend_idx, type_name in enumerate(backend_legend["tokenTypes"]):
        canonical_idx = _CANONICAL_TYPE_INDEX.get(type_name, -1)
        mapping[backend_idx] = canonical_idx
    return mapping


def build_modifier_mapping(
    backend_legend: types.SemanticTokensLegend,
) -> dict[int, int]:
    """Build mapping from backend modifier bit positions to canonical positions."""
    mapping: dict[int, int] = {}
    for backend_bit, modifier_name in enumerate(backend_legend["tokenModifiers"]):
        canonical_bit = _CANONICAL_MODIFIER_INDEX.get(modifier_name, -1)
        mapping[backend_bit] = canonical_bit
    return mapping


def normalize_tokens(
    tokens: types.SemanticTokens,
    type_map: dict[int, int],
    modifier_map: dict[int, int],
) -> types.SemanticTokens:
    """Remap token indices to use canonical legend."""
    data = tokens.get("data", [])
    if not data:
        return tokens

    # Each token is 5 integers: deltaLine, deltaStart, length, typeIndex, modifiers
    normalized_data: list[int] = []

    for i in range(0, len(data), 5):
        if i + 4 >= len(data):
            break  # Incomplete token data

        delta_line = data[i]
        delta_start = data[i + 1]
        length = data[i + 2]
        type_index = data[i + 3]
        modifier_bits = data[i + 4]

        # Remap token type index
        canonical_type = type_map.get(type_index, type_index)
        if canonical_type == -1:
            canonical_type = type_index  # Keep original if unknown

        # Remap modifier bitmask
        canonical_modifiers = 0
        for backend_bit, canonical_bit in modifier_map.items():
            if modifier_bits & (1 << backend_bit):
                if canonical_bit >= 0:
                    canonical_modifiers |= 1 << canonical_bit

        normalized_data.extend(
            [
                delta_line,
                delta_start,
                length,
                canonical_type,
                canonical_modifiers,
            ]
        )

    result: types.SemanticTokens = {"data": normalized_data}
    if "resultId" in tokens:
        result["resultId"] = tokens["resultId"]

    return result
