"""Regression coverage for Pyrefly string highlighting."""

from pathlib import Path

from lsp_types import Session, types
from lsp_types.pyrefly.backend import PyreflyBackend
from lsp_types.semantic_tokens import (
    CANONICAL_LEGEND,
    PYREFLY_LEGEND,
    build_modifier_mapping,
    build_type_mapping,
    normalize_tokens,
)


def test_pyrefly_string_modifier_bits_survive_normalization():
    # Check each wire bit separately so swapped mappings cannot hide behind
    # an identical aggregate mask. Preserve the existing canonical indices.
    for wire_bit, canonical_bit in (
        (11, 14),
        (12, 19),
        (13, 20),
        (14, 21),
        (15, 15),
        (16, 16),
        (17, 17),
        (18, 18),
    ):
        raw: types.SemanticTokens = {
            "data": [0, 4, 3, 18, (1 << wire_bit) | 4],
            "resultId": "strings",
        }
        normalized = normalize_tokens(
            raw,
            build_type_mapping(PYREFLY_LEGEND),
            build_modifier_mapping(PYREFLY_LEGEND),
        )
        assert normalized == {
            "data": [0, 4, 3, 18, (1 << canonical_bit) | 4],
            "resultId": "strings",
        }
        assert raw["data"][-1] == (1 << wire_bit) | 4


async def test_pyrefly_live_string_highlighting(tmp_path: Path):
    session = await Session.create(
        PyreflyBackend(),
        base_path=tmp_path,
        initial_code=(
            'a = b"bytes"\nb = r"raw"\nc = f"{a}"\nd = t"{a}"\n'
            'e = "\\n"\nf = "%s" % a\ng = f"{1:04d}"\n'
        ),
        options={"python_version": "3.14"},
    )
    try:
        tokens = await session.get_semantic_tokens(normalize=True)
        assert tokens is not None
        modifiers = {
            name
            for mask in tokens["data"][4::5]
            for bit, name in enumerate(CANONICAL_LEGEND["tokenModifiers"])
            if mask & (1 << bit)
        }
        assert {
            "byteString",
            "rawString",
            "formatString",
            "stringPrefix",
            "templateString",
            "escapeSequence",
            "formatPlaceholder",
            "formatSpecifier",
        } <= modifiers
    finally:
        await session.shutdown()
