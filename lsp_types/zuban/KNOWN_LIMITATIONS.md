# 🛡️ Zuban: behavior & limitations

## Configuration replaces `[tool.zuban]`

`ZubanBackend` adds or replaces `[tool.zuban]` in `pyproject.toml`, including when
`options` is empty. That table selects Zuban's native `default` mode; a project
with only `[tool.mypy]` uses Mypy-compatible defaults instead.

Other sections retain their values, comments, layout, and line endings. The
previous `[tool.zuban]` table and its associated comments are replaced.
`mypy.ini`, `.mypy.ini`, and `setup.cfg` are not read or edited by the backend's
configuration writer.

`Session.create()` defaults to the current directory. Set `base_path` to a
dedicated directory to keep session settings separate from your project.

## Unused ignores are not reported

Zuban does not flag unused `# type: ignore` comments.

## Value-constrained generic bodies are not checked

Zuban skips type checking inside functions parameterized by
`TypeVar("T", str, bytes)` or `[T: (str, bytes)]`. Type errors in those bodies do
not appear in diagnostics. Upper-bounded TypeVars, such as
`TypeVar("T", bound=str)`, are checked normally.

Both gaps are listed in Zuban's
[missing features](https://docs.zubanls.com/en/latest/features.html).

## Server settings use TOML or initialization options

`zuban server` accepts no configuration flags. Configure it through `options`
or pass LSP settings through `initialize_params`:

```python
initialize_params = {
    "initializationOptions": {"diagnosticMode": "workspace"}
}
```

Zuban supports `typeCheckingMode`, `disableLanguageServices`, `diagnosticMode`,
`pythonExecutable`, and `inlayHintMode` initialization settings. Recreate the
session to change configuration; the backend skips
`workspace/didChangeConfiguration`.

`typeCheckingMode="off"` and `disableLanguageServices=True` remove the
corresponding advertised capabilities, but direct diagnostic, hover, and
completion requests still return results. `Session` sends these requests
unconditionally. Enforce disabled features in your application.
