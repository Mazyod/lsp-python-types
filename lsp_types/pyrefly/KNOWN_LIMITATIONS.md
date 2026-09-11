# Pyrefly backend: known limitations

Verified with **Pyrefly 1.3.0 on 2026-09-11** using this library's LSP client.
Release notes are dated September 10; PyPI and GitHub publication occurred
September 11 UTC. [Release](https://github.com/facebook/pyrefly/releases/tag/1.3.0)

## Completion resolution is an echo

`completionItem/resolve` returns the submitted item unchanged, despite
advertising `completionProvider.resolveProvider: true`. A live probe resolved
a method completion both normally and with `detail`/`documentation` removed;
both responses exactly matched their respective inputs.

Initial completions already include type details and documentation, so ordinary
completion remains useful. Calling `resolve_completion()` succeeds but does
not retrieve additional metadata.

## Semantic-token legend is not advertised

The initialize response omits `semanticTokensProvider` entirely, while
`textDocument/semanticTokens/full` still returns tokens. The backend therefore
supplies `PYREFLY_LEGEND` instead of discovering a legend from the server.

Pyrefly 1.3.0 adds five string modifiers: `byteString`, `formatString`,
`rawString`, `stringPrefix`, and `templateString` (bits 11–15). This maintenance
updates both the fallback legend and canonical modifiers so normalization
preserves those bits. Token types are unchanged. See
[semantic-token documentation](../../docs/SEMANTIC_TOKENS.md).

## Configuration and API boundaries

The backend writes kebab-case TOML keys from top-level snake_case Python keys.
Nested error-code keys should use the upstream names (`bad-assignment`, etc.).
The typed schema covers common options; a plain `Session.create(options=...)`
dictionary can carry other upstream settings.

Upstream CLI tools, TSP, and editor refactorings extend beyond the high-level
`Session` API. Their availability upstream does not imply a matching Session
method. Tensor-shape and DataFrame schema extensions remain experimental.

## Previously resolved

Rename previously failed for session files classified as external. It has
worked since 1.1.1 and remains covered by the regular rename integration test;
the former expected failure is gone. Virtual documents work without on-disk
mirroring.
