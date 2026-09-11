# 🔧 Backend integration

`Session` provides one API for Pyright, basedpyright, Pyrefly, ty, and Zuban.
Each backend supplies its launch command, configuration, and capabilities.
All supported backends analyze virtual documents without writing Python files
to disk.

## Configuration

`Session.create(options=...)` writes configuration in `base_path` before
launching the server. The default `base_path` is the current directory.

| Backend | Configuration file | Python option keys |
| --- | --- | --- |
| Pyright / basedpyright | `pyrightconfig.json` | Upstream camelCase |
| Pyrefly | `pyrefly.toml` | Top-level snake_case becomes kebab-case; nested keys keep their spelling |
| ty | `ty.toml` | Snake_case becomes kebab-case recursively |
| Zuban | `[tool.zuban]` in `pyproject.toml` | Snake_case, unchanged |

Pyright, Pyrefly, and ty replace their configuration files. Zuban replaces only
`[tool.zuban]`, preserving other sections and their formatting. Use a dedicated
`base_path` to keep session configuration separate from an existing project.

Pass server-specific LSP initialization settings through
`Session.create(initialize_params=...)`. These values override the corresponding
top-level initialization fields. ty and Zuban receive configuration at session
creation; recreate their sessions to apply changes.

## Capabilities and results

- **Semantic tokens:** basedpyright, Pyrefly, ty, and Zuban support them.
  Microsoft Pyright does not. Use the [normalized token API](SEMANTIC_TOKENS.md)
  for one editor legend across backends.
- **Hover:** content and formatting differ by server. Display the returned
  content directly; ty's variable hover shows the type without the variable name.
- **Completion resolution:** Pyrefly returns the submitted item unchanged.
  ty rejects resolution requests. Use their initial completion results.
- **External file changes:** the client does not watch files. Recreate a session
  when files changed outside `update_code()` are not reflected in results.

See the backend-specific guidance for [Pyrefly](../lsp_types/pyrefly/KNOWN_LIMITATIONS.md),
[ty](../lsp_types/ty/KNOWN_LIMITATIONS.md), and
[Zuban](../lsp_types/zuban/KNOWN_LIMITATIONS.md).

## Adding a backend

Implement `LSPBackend` with the server's configuration writer, launch command,
client capabilities, workspace settings, and semantic-token legend fallback.
Use `None` for the fallback when the server advertises its legend.

Set `requires_file_on_disk()` to match the server's document requirements.
Set `consumes_did_change_configuration()` to `False` when the server does not
handle that notification. `Session` handles initialization, document updates,
requests, and shutdown.
