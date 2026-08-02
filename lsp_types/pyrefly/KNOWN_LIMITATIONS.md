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

These limitations were last verified with Pyrefly 1.2.0 (August 2026): `completionItem/resolve` remains a no-op (the resolved item is returned byte-identical), and the semantic-tokens legend is still not advertised via LSP (`semanticTokensProvider` has no legend in the initialize result), so the hardcoded `PYREFLY_LEGEND` remains required. Future versions may address some of these limitations.
