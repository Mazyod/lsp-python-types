# Feature Verification Guide

This document describes how to verify and update the feature support matrix in the README.

## Verification Process

### Step 1: Run the Test Suite

```bash
uv run pytest tests/test_session.py -v
```

Tests are parametrized across all backends (Pyright, Pyrefly, ty, Zuban). Key indicators:
- **PASSED**: Feature works for that backend
- **XFAIL**: Known limitation, documented with reason
- **FAILED**: Regression or new issue

### Step 2: Review xfail Markers

In `tests/`, search for `xfail` to find documented limitations:

```python
# Example from test_pool.py::test_session_warmup_on_recycle:
if backend_name == "ty":
    pytest.xfail("ty hover doesn't include variable names in output")
```

Each xfail message explains why the feature is limited.

### Step 3: Check Backend Capabilities

Each backend declares its LSP capabilities in `get_lsp_capabilities()`:
- `lsp_types/pyright/backend.py`
- `lsp_types/pyrefly/backend.py`
- `lsp_types/ty/backend.py`
- `lsp_types/zuban/backend.py`

Features declared here indicate what the client advertises to the server.

### Step 4: Review Known Limitations

- [Pyrefly Known Limitations](../lsp_types/pyrefly/KNOWN_LIMITATIONS.md)
- [ty Known Limitations](../lsp_types/ty/KNOWN_LIMITATIONS.md)
- [Zuban Known Limitations](../lsp_types/zuban/KNOWN_LIMITATIONS.md)

## Updating the Feature Table

### When to Update

1. **After adding new Session API methods**: Add test, run it, update table
2. **After upgrading backend versions**: Re-run tests, check for improvements, update version line
3. **After backend releases announce new features**: Test and document

### Updating Version Numbers

Update the "Last verified" line in README when re-testing:

```bash
# Check installed versions
pyright --version      # or basedpyright --version
pyrefly --version
ty --version
zuban --version
```

### Status Symbols

| Symbol | Meaning | When to Use |
|--------|---------|-------------|
| :white_check_mark: | Fully supported | Test passes without xfail |
| :warning: | Partial support | Test has xfail or conditional skip |
| :x: | Not supported | Feature fails or is documented as unsupported |
| :grey_question: | Unknown | Not exposed in Session API or not tested |

### Adding Notes

- Keep notes concise (under 50 characters)
- Reference the specific limitation (e.g., "shows type only, not variable name")
- Use semicolons to separate multiple backend notes

## Evidence Mapping

| Feature | Test Function | What to Check |
|---------|---------------|---------------|
| Diagnostics | `test_session_diagnostics` | All backends pass; virtual documents work everywhere (ty since 0.0.16) |
| Hover | `test_session_hover` | All backends pass; `if backend_name != "ty"` guards the variable-name assertion (ty shows type only) |
| Completion | `test_session_completion` | All backends pass |
| Completion Resolution | `test_session_completion` | `if backend_name != "ty"` skips resolution for ty only (it errors `-32601`). Pyrefly is invoked but only its echo is asserted, which is why the README still marks it unsupported |
| Signature Help | `test_session_signature_help` | No xfails expected |
| Rename | `test_session_rename` | All backends pass; Pyrefly rename was fixed in 1.1.1 (the former xfail is removed) |
| Semantic Tokens | `test_session_semantic_tokens` | No xfails expected |

## Untested Features

Features declared in backend capabilities but not exposed in Session API:
- Go to Definition (Pyrefly, ty, Zuban declare it)
- Find References (Pyrefly, ty, Zuban declare it)
- Code Actions
- Formatting

To test these, use the low-level `LSPProcess` API directly.
