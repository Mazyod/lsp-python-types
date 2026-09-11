# Python language servers: a field guide

Research snapshot: **2026-09-11**. These are upstream capabilities and design
choices, not a claim that every feature is exposed by this library's `Session`
API. See [feature verification](../FEATURE_VERIFICATION.md) for local evidence.
The README's characters are playful descriptions of priorities, not performance
ratings or predictions of reliability.

## Release snapshot

- **Pyright 1.1.414**, September 9: typing fixes, type-equality optimization,
  and publication of `pyright-typeserver` to npm.
  [Release notes](https://github.com/microsoft/pyright/releases/tag/1.1.414).
- **basedpyright 1.40.1**, September 10: merges Pyright 1.1.414 and improves
  multiline builtin docstring display.
  [Release notes](https://github.com/DetachHead/basedpyright/releases/tag/v1.40.1).
- **ty 0.0.80**, September 9: fixes hangs during bursts of inlay-hint requests,
  gives autofixes more descriptive names, and improves typing and memory usage.
  Since the previous local 0.0.75 snapshot, 0.0.76 also added a preview rule for
  missing direct dependencies and improved PEP 723 script environments.
  [0.0.80](https://github.com/astral-sh/ty/releases/tag/0.0.80),
  [0.0.76](https://github.com/astral-sh/ty/releases/tag/0.0.76).
- **Zuban 0.9.3**, September 2: deterministic file processing and a fix for
  quadratic behavior involving literals.
  [Release](https://github.com/zubanls/zuban/releases/tag/v0.9.3),
  [changelog](https://docs.zubanls.com/en/latest/changelog.html).

The versions above were checked against live package registries and explicit
release tags. Cached GitHub `/releases/latest` pages returned older versions for
Zuban and basedpyright during this run; search-result dates alone are insufficient.

## Pyright — the veteran

Pyright remains a broad, configurable type checker. Its execution environments
let different project subdirectories target different Python versions, platforms,
and import paths. Its language server includes call hierarchy, navigation,
rename, completions and stub generation. These make a useful established
reference without implying that it wins every comparison.
[Pyright features at 1.1.414](https://github.com/microsoft/pyright/blob/1.1.414/docs/features.md).

**Tradeoff:** Pyright, Pylance and basedpyright are different products. In
particular, semantic highlighting, inlay hints and import quick fixes are among
the Pylance features independently implemented by basedpyright; a successful
basedpyright test does not establish vanilla Pyright support.
[basedpyright's LSP additions](https://docs.basedpyright.com/latest/benefits-over-pyright/pylance-features/).

## basedpyright — the guardian with adjustable armor

This fork adds stricter defaults and finer diagnostic controls to the Pyright
family. Its recommended mode enables all diagnostic rules, uses warnings for
some checks, and checks all platforms by default. Expect adoption to surface
more issues unless the project config relaxes those defaults.
[Defaults](https://docs.basedpyright.com/latest/benefits-over-pyright/better-defaults/).

Its baseline records existing errors so new work can face stricter checks
without first fixing the whole codebase. Baselines work in both CLI and LSP;
matching is imperfect when code moves. Editor additions include enum and
non-string literal completions, automatic `@override` insertion, and configurable
hint severity. These are concrete customization strengths, not just parity.
[Baseline](https://docs.basedpyright.com/latest/benefits-over-pyright/baseline/),
[editor improvements](https://docs.basedpyright.com/latest/benefits-over-pyright/language-server-improvements/).

## ty — the swift scout

ty's architecture prioritizes fine-grained incremental analysis: edits should
invalidate only the computations that depend on them. Its diagnostics emphasize
context and explanations. That makes quick feedback and understandable errors
a more useful identity than simply “written in Rust.”
[Astral's design and benchmark discussion](https://astral.sh/blog/ty).

The type system also has its own character: it permits variable redeclarations,
uses intersections for narrowing, and reasons about reachability using inferred
types. Its `hasattr` analysis accounts for subclasses adding an attribute.
Explicit `ty_extensions.Intersection` annotations are ty-specific and currently
available only during type checking; the internal inference benefits do not
require adopting those annotations.
[Type-system examples](https://docs.astral.sh/ty/features/type-system/).

Configuration offers per-file rule and analysis overrides, selective treatment
of third-party imports, and opt-in stricter equality and generic narrowing.
The last two default to false: extra theoretical precision can produce types
that are less convenient for everyday code.
[Configuration reference](https://docs.astral.sh/ty/reference/configuration/).

**Tradeoff:** this integration has its own documented completion-resolution,
hover-format and file-watching constraints. A missing client feature is not a
general verdict on ty's editor support. Consult the
[locally verified limitations](../../../lsp_types/ty/KNOWN_LIMITATIONS.md).

## Zuban — the bridge builder

Zuban's distinctive combination is Mypy migration and help with untyped code.
Its Mypy mode preserves familiar configuration and behavior, while native mode
checks untyped functions and infers their returns. The LSP's automatic mode
selection is influenced by project configuration; this library writes
`[tool.zuban]`, which selects native mode unless explicitly overridden.
[Modes and configuration](https://docs.zubanls.com/en/latest/usage.html#modes).

Since 0.8.0, editor heuristics follow call sites to improve completion, hover,
navigation and signatures even where the checker still sees `Any`. This is an
explicit distinction between editor assistance and type-checking semantics.
Earlier releases added Django model support, notebook support and completion
documentation resolution.
[Changelog](https://docs.zubanls.com/en/latest/changelog.html).

**Tradeoff:** upstream still documents unchecked bodies of functions with
value-constrained TypeVars and missing unused-ignore diagnostics. General Mypy
plugin compatibility is not planned; targeted library support is different.
Zuban currently uses one CPU core and targets low memory consumption. Call/type
hierarchy and file-rename import updates are absent from its documented LSP
capabilities. These are more actionable limits than calling it “less capable.”
[Capabilities and missing features](https://docs.zubanls.com/en/latest/features.html).

## Reading performance claims fairly

Astral's December 2025 announcement reports separate cold CLI and incremental
LSP measurements: Home Assistant checking without cache, and diagnostic
recomputation after an edit in PyTorch on an M4. Its striking multipliers describe
those workloads and historical versions; they are not current universal rankings.
[Benchmark context](https://astral.sh/blog/ty).

Zuban's homepage claims substantial speedups over Mypy and lower CPU/memory than
ty and Pyrefly. These are upstream claims, not measurements made by this project.
Likewise, passing over 95% of the *relevant Mypy tests* is a specific compatibility
measure, not a score for LSP quality or all Python programs.
[Zuban's overview](https://docs.zubanls.com/en/latest/).

A useful local comparison must fix versions, interpreter, config and workload;
separate process startup, cold project checking and warm edits; check equivalent
diagnostic work; and report repeated measurements with machine details. The
integration suite establishes functionality, not a speed leaderboard. No README
character implies “fastest,” “slow,” or “breaks easily.”

## Maintenance findings

The upstream review led to these maintenance changes:

- ty's typed config now includes analysis import controls and strictness options,
  per-file analysis overrides and script exclusions. Its output-format choices
  and warning-exit default were refreshed against the
  [reference](https://docs.astral.sh/ty/reference/configuration/).
- Zuban's typed mode choices now include `auto`, added in 0.9.0. Fresh live probes
  confirmed that its constrained-TypeVar and unused-ignore limitations remain.
  [Changelog](https://docs.zubanls.com/en/latest/changelog.html).
- Vanilla Pyright and basedpyright now have independent test runs. Editor
  extension features are no longer credited to vanilla Pyright through a shared
  backend name.
- TSP is separate from this library's LSP integration. Pyright's newest release
  also publishes a type server, so that category is not exclusive to Pyrefly.
  [Pyright 1.1.414](https://github.com/microsoft/pyright/releases/tag/1.1.414).
