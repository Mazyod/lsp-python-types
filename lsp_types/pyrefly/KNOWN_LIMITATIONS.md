# Pyrefly Backend - Known Limitations

This document describes known limitations and behavioral differences when using the Pyrefly backend compared to other LSP backends (Pyright, ty).

## 1. Rename Operations Disabled for External Files

**Limitation**: Pyrefly detects files as "external" and disables rename edit functionality.

**Behavior**: Calling `get_rename_edits()` returns `None` or empty edits for files that Pyrefly considers external to the project.

**Impact**: Symbol renaming may not work in certain project configurations.

**Status**: Marked as xfail in tests pending investigation.

## 2. Completion Item Resolution Not Supported

**Limitation**: Pyrefly does not support the `completionItem/resolve` LSP request.

**Behavior**: Calling `resolve_completion()` may return the item unchanged without additional details.

**Impact**: Completion items won't have extended documentation or additional metadata that resolution typically provides.

## 3. Configuration Key Format

**Note**: Pyrefly uses TOML configuration (`pyrefly.toml`) with kebab-case keys (e.g., `python-version`, `search-path`). The backend automatically converts snake_case Python keys to kebab-case when writing the config file.

---

## Version Information

These limitations were documented based on Pyrefly version 0.32.0+. Future versions may address some of these limitations.
