# Choose your language server

Each member of the party brings a different strength. All use the same
[`Session` API](../USAGE.md).

| Backend | Reach for it when you want… |
|---|---|
| 🛡️ Pyright | Broad typing support and separate environments within one project |
| ⚔️ basedpyright | Stricter diagnostics, baselines and richer editor features |
| 🔧 [Pyrefly](pyrefly.md) | Framework-aware analysis and specialized checks |
| 🏹 ty | Incremental analysis and explanatory diagnostics |
| 🤝 Zuban | Mypy migration and editor assistance for untyped code |

## Pyright — the sentinel

Pyright combines broad typing support with configurable execution environments.
Different project directories can target different Python versions, platforms
and import paths. Its language server provides completion, navigation, rename
and call hierarchy. [Pyright features](https://github.com/microsoft/pyright/blob/1.1.414/docs/features.md).

Microsoft Pyright does not provide semantic tokens. Choose **basedpyright** for
semantic highlighting and additional editor features. Both work with
`PyrightBackend`; install the distribution you want to run.

## basedpyright — the guardian

basedpyright adds stricter defaults, finer diagnostic controls and a baseline
for existing errors. Use the baseline to enforce checks on new work while
addressing older errors gradually. Its recommended mode enables all diagnostic
rules, assigns warnings to some checks and checks all platforms by default.
[Defaults](https://docs.basedpyright.com/latest/benefits-over-pyright/better-defaults/),
[baselines](https://docs.basedpyright.com/latest/benefits-over-pyright/baseline/).

Editor additions include semantic highlighting, inlay hints, import quick fixes,
enum and literal completions, and automatic `@override` insertion.
[Editor features](https://docs.basedpyright.com/latest/benefits-over-pyright/pylance-features/),
[completion improvements](https://docs.basedpyright.com/latest/benefits-over-pyright/language-server-improvements/).

## Pyrefly — the artificer

🔧 Pyrefly combines framework-aware analysis with specialized checks. It
understands same-file Django reverse relations, SQLAlchemy updates and PyTorch
registered attributes. Opt-in diagnostics validate literal regexes and
`mock.patch` targets. Tensor-shape and DataFrame schema analysis are experimental.

`PyreflyBackend` provides diagnostics, hover, completion, signature help, rename
and semantic tokens through `Session`. Initial completion items include type
details and documentation; `resolve_completion()` returns the item unchanged.
The backend supplies the semantic-token legend automatically.

See the [Pyrefly guide](pyrefly.md) for configuration examples and specialized tools.

## ty — the scout

ty uses fine-grained incremental analysis to recompute work affected by an edit.
Its diagnostics explain errors with context, and its type system uses
intersections and reachability analysis to narrow types.
[Astral's design](https://astral.sh/blog/ty),
[type system](https://docs.astral.sh/ty/features/type-system/).

Configuration supports per-file overrides and controls for third-party import
analysis. Stricter equality and generic narrowing are opt-in settings.
[Configuration reference](https://docs.astral.sh/ty/reference/configuration/).

In `Session`, ty hover returns the type without the variable name. Completion
works; `resolve_completion()` raises `-32601`. Recreate the session after
configuration changes or external file edits.
[Integration details](../../lsp_types/ty/KNOWN_LIMITATIONS.md).

## Zuban — the diplomat

Zuban bridges Mypy workflows and editor assistance for untyped code. Mypy mode
preserves familiar defaults; native mode checks untyped functions and infers
return types. `ZubanBackend` writes `[tool.zuban]`, selecting native mode unless
you override it. [Modes and configuration](https://docs.zubanls.com/en/latest/usage.html#modes).

Its editor heuristics use call sites to improve completion, hover, navigation
and signatures in untyped code. It also supports Django models and notebooks.
[Zuban features](https://docs.zubanls.com/en/latest/features.html).

Zuban does not check value-constrained `TypeVar` function bodies or report unused
`# type: ignore` comments. Upper-bounded `TypeVar` bodies are checked. General
Mypy plugin compatibility is not supported.
[Integration details](../../lsp_types/zuban/KNOWN_LIMITATIONS.md).

## Using these features

`Session` provides diagnostics, hover, completion, signature help, rename and
semantic tokens where supported. Use the typed
[`LSPProcess` API](../USAGE.md#low-level-stdio) for additional protocol requests
such as navigation and call hierarchy.
