# ⚡ ty: behavior & limitations

## Configuration applies at session creation

`TyBackend` writes `options` to `ty.toml`, converting snake_case keys to
kebab-case recursively. ty does not handle `workspace/didChangeConfiguration`,
so the backend skips that notification. Recreate the session to change settings.

Pass inline configuration through `Session.create(initialize_params=...)`,
using upstream kebab-case keys:

```python
initialize_params = {
    "initializationOptions": {
        "configuration": {"rules": {"unresolved-import": "ignore"}}
    }
}
```

Misspelled nested settings, including `unresolved_import` in this example, are
silently ignored. `ty server` accepts no configuration flags. Use `ty.toml` or
LSP initialization options, including `logLevel` and `configurationFile`.
See the [editor settings reference](https://docs.astral.sh/ty/reference/editor-settings/).

## Hover omits the variable name

Variable hover displays the type, such as `str` or `Literal["ok"]`, without the
variable name. Display the response directly rather than parsing it as
`name: type`.

## Workspace folders need explicit initialization

Without `workspaceFolders`, ty uses the server's working directory and logs a
warning. `Session` does not populate this field automatically. Supply it through
`initialize_params` when you need explicit workspace roots:

```python
initialize_params = {
    "workspaceFolders": [{"uri": root.as_uri(), "name": root.name}]
}
```

Here, `root` is an absolute `pathlib.Path` to an existing workspace directory.

## External files are not watched

The client does not install file watchers. ty reports this with a warning;
files changed by external tools can remain stale until the session is recreated.
Document edits sent through `update_code()` work normally.

## Completion resolution is unsupported

`resolve_completion()` raises `Unknown request: completionItem/resolve (-32601)`.
Use the initial completion response.

## Virtual documents are supported

Supported ty versions analyze documents opened through LSP without a matching
Python file on disk. The backend requires ty 0.0.16 or newer.
