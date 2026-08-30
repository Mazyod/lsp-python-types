# Pyrefly Backend - Known Limitations

This document describes known limitations and behavioral differences when using the Pyrefly backend compared to other LSP backends (Pyright, ty).

## 1. Completion Item Resolution Is a No-op

**Limitation**: Pyrefly accepts the `completionItem/resolve` LSP request but returns the item unchanged.

**Behavior**: Calling `resolve_completion()` does not raise (unlike ty), but the resolved item carries no additional `detail`, `documentation`, or other metadata beyond what the initial completion already provided.

**Impact**: Completion items won't gain extended documentation from resolution. Basic completion works fine.

## 2. Configuration Key Format

**Note**: Pyrefly uses TOML configuration (`pyrefly.toml`) with kebab-case keys (e.g., `python-version`, `search-path`). The backend automatically converts snake_case Python keys to kebab-case when writing the config file.

---

## Previously Documented, Now Resolved

- **Rename operations disabled for external files** (documented for Pyrefly 0.32.0): Earlier Pyrefly versions treated session files as "external" and returned no rename edits, so `get_rename_edits()` was marked `xfail`. As of Pyrefly 1.1.1 rename returns proper edits and the test is now a regular passing case.

---

## Version Information

These limitations were last verified with Pyrefly 1.2.0 (verified 2026-08-30;
1.2.0 is the newest stable release on PyPI, released 2026-08-01):

- `completionItem/resolve` remains a no-op. The resolved item comes back
  byte-identical, and an item with `detail`/`documentation` stripped before the
  request comes back still stripped — a pure echo, not an already-complete
  result. Pyrefly nonetheless advertises `completionProvider.resolveProvider:
  true`. Little is lost in practice: Pyrefly front-loads `detail` and
  `documentation` into the initial completion items.
- The semantic-tokens legend is still not advertised: `semanticTokensProvider`
  is absent from the initialize result entirely (not merely missing its
  `legend`), even though the server answers `textDocument/semanticTokens/full`.
  The hardcoded `PYREFLY_LEGEND` therefore remains required. ty and Zuban both
  advertise a legend.
- Rename returns proper edits for the virtual session document and spans
  on-disk sibling modules; the fix has not regressed.

**Forward-looking:** Pyrefly `main` (heading to 1.3.0) appends five token
modifiers after `selfParameter` — `byteString`, `formatString`, `rawString`,
`stringPrefix`, `templateString` (bits 11-15). Verified against 1.3.0.dev3:
those bits are emitted and silently dropped by `normalize_tokens()` because
they are absent from both `PYREFLY_LEGEND` and `CANONICAL_TOKEN_MODIFIERS`.
Both lists must be extended when 1.3.0 ships. Token *types* are unchanged.
