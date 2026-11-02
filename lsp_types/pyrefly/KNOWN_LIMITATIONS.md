# 🪽 Pyrefly: behavior & limitations

## Completion resolution adds no details

`resolve_completion()` returns the submitted item unchanged. Use the type
details and documentation included in the initial completion response.

## Semantic-token legend uses a built-in fallback

`PyreflyBackend` requires Pyrefly 1.4.0 or newer and supplies `PYREFLY_LEGEND`
for its full token stream. Pyrefly advertises a legend only when the client
sets `augmentsSyntaxTokens=True`; that mode omits syntax tokens such as strings.

Normalization preserves Pyrefly's string modifiers: `byteString`,
`formatString`, `rawString`, `stringPrefix`, `templateString`, `escapeSequence`,
`formatPlaceholder`, and `formatSpecifier`. See the
[semantic-token guide](../../docs/SEMANTIC_TOKENS.md).

## Configuration keys

Top-level snake_case Python keys become kebab-case TOML keys. Nested keys keep
their spelling: use upstream error-code names such as `bad-assignment`.
The typed schema covers common options; `Session.create(options=...)` also
accepts a plain dictionary with other upstream settings.

## API scope

Virtual documents and rename work without on-disk mirroring. The high-level
`Session` API exposes the methods documented by this library; upstream CLI,
TSP, and editor-only features do not automatically become session methods.
