# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

Always use `uv` for Python operations:

```bash
# Run tests
uv run pytest                                  # All tests
uv run pytest tests/test_pool.py               # Pool tests
uv run pytest tests/test_session.py            # Session tests
uv run pytest tests/test_pool.py::TestLSPProcessPool::test_name -v  # Single test

# Type checking (required before committing)
# NOTE: --pythonpath is required to resolve the virtual environment correctly
uvx pyright --pythonpath .venv/bin/python      # Run pyright type checker
uvx pyright --pythonpath .venv/bin/python lsp_types/   # Check only library code
uvx pyright --pythonpath .venv/bin/python tests/       # Check only test code

# Linting and formatting (required before committing)
uvx ruff check .                               # Check for linting errors
uvx ruff check . --fix                         # Auto-fix linting errors
uvx ruff format .                              # Format code
uvx ruff check . --select I --fix              # Sort imports

# Generate latest LSP types (full pipeline)
make generate-latest-types                     # Downloads schemas + generates all types

# Individual generation steps
make download-schemas                          # Download latest LSP schemas
make generate-lsp-schema                       # Generate main LSP types
make generate-pyright-schema                   # Generate Pyright config types
make generate-types                            # Generate final type definitions
```

## Architecture Overview

This is a minimal-dependency Python library providing typed LSP (Language Server Protocol) interfaces with optional process management.

### Core Components

**Generated Types System (`lsp_types/types.py`)**
- Auto-generated from official LSP JSON schemas using `datamodel-code-generator`
- Provides TypedDict definitions for all LSP protocol structures
- Source schemas in `assets/lsprotocol/` and `assets/lsps/`
- Generation pipeline in `assets/scripts/`

**Process Management (`lsp_types/process.py`)**
- `LSPProcess`: Core async LSP communication over stdio
- `ProcessLaunchInfo`: Configuration for launching LSP servers
- Handles JSON-RPC protocol, message framing, and async request/response correlation
- Provides `.send` (requests) and `.notify` (notifications) interfaces

**Session System (`lsp_types/session.py`)**
- `Session`: Concrete LSP session implementation using pluggable backends
- `LSPBackend`: Protocol defining backend-specific operations (config, process launch, capabilities)
- Consolidated implementation with common LSP functionality shared across all backends
- Standard interface for `shutdown()`, `update_code()`, `get_diagnostics()`, etc.

**Request/Notification Functions (`lsp_types/requests.py`)**
- `RequestFunctions`: Typed async methods for all LSP requests (initialize, hover, completion, etc.)
- `NotificationFunctions`: Typed methods for LSP notifications (initialized, didOpen, didChange, etc.)
- Auto-generated from LSP schema to provide full protocol coverage
- Used internally by `LSPProcess.send` and `LSPProcess.notify` interfaces

**Generic Process Pooling (`lsp_types/pool.py`)**
- `LSPProcessPool`: Language-server agnostic process pooling for performance optimization
- `ProcessMetadata`: TypedDict of per-process pool bookkeeping (`base_path`, `compatibility_key`, `idle_since`)
- Reusable across different LSP implementations (not just Pyright)
- Handles process lifecycle: creation, reuse, idle cleanup, and shutdown

**Semantic Tokens Normalization (`lsp_types/semantic_tokens.py`)**
- `CANONICAL_LEGEND`: Fixed canonical legend for Monaco/editor integration
- `CANONICAL_TOKEN_TYPES`, `CANONICAL_TOKEN_MODIFIERS`: LSP standard types/modifiers plus backend-specific
- `build_type_mapping()`, `build_modifier_mapping()`: Create index mapping tables
- `normalize_tokens()`: Remap token indices from backend-specific to canonical legend
- `PYREFLY_LEGEND`: Hardcoded legend for Pyrefly (doesn't advertise via LSP)
- Used by `Session.get_semantic_tokens(normalize=True)` for backend-agnostic tokens

**Backend Integrations**

**Pyright Integration (`lsp_types/pyright/`)**
- `backend.py`: `PyrightBackend` implementation for Pyright LSP server
- `config_schema.py`: Auto-generated Pyright configuration types
- **Key Design**: Uses consolidated `Session` class with `PyrightBackend` for specialization

**Pyrefly Integration (`lsp_types/pyrefly/`)**
- `backend.py`: `PyreflyBackend` implementation for Pyrefly LSP server (Facebook's Rust-based type checker)
- `config_schema.py`: Pyrefly configuration types (TypedDict with known fields)
- **Key Design**: Uses consolidated `Session` class with `PyreflyBackend` for specialization
- **Config Flexibility**: Supports arbitrary configuration fields via TOML serialization (using `tomlkit`)

**ty Integration (`lsp_types/ty/`)**
- `backend.py`: `TyBackend` implementation for ty LSP server (Astral's Rust-based type checker)
- `config_schema.py`: ty configuration types with nested sections (environment, src, rules, etc.)
- **Key Design**: Uses consolidated `Session` class with `TyBackend` for specialization
- **Config Format**: TOML (`ty.toml`) with nested sections and kebab-case keys
- **Virtual Documents**: Supported since ty 0.0.16 — no on-disk mirroring needed
- **Documentation**: See `KNOWN_LIMITATIONS.md` in the ty package for details

**Zuban Integration (`lsp_types/zuban/`)**
- `backend.py`: `ZubanBackend` implementation for Zuban LSP server (Rust-based type checker + LSP by the author of Jedi)
- `config_schema.py`: Zuban configuration types (TypedDict with known fields; arbitrary Mypy-compatible fields pass through)
- **Key Design**: Uses consolidated `Session` class with `ZubanBackend` for specialization
- **Config Format**: `pyproject.toml` with `[tool.zuban]` table; snake_case keys (no kebab conversion)
- **Virtual Documents**: Supported — no on-disk mirroring needed
- **Documentation**: See `KNOWN_LIMITATIONS.md` in the zuban package for details

### Type Generation Pipeline

**Schema Sources:**
- `assets/lsprotocol/lsp.schema.json`: Official LSP protocol schema
- `assets/lsps/pyright.schema.json`: Pyright-specific configuration schema
- `assets/lsps/pyrefly-guide.md`: Pyrefly configuration documentation (manually defined types)

**Generation Process:**
1. `download_schemas.py`: Fetches latest schemas from upstream
2. `datamodel-codegen`: Converts JSON schema to TypedDict definitions, pinned to
   `--formatters black isort`, then ruff-formats its own output
3. `generate.py`: Orchestrates final type file generation with utilities in `assets/scripts/utils/`
4. Every file in the Makefile's `GENERATED_FILES` is ruff-formatted and `--fix`ed so
   regenerating produces no spurious diff

The generation targets need `make`. If it is unavailable, run the recipes from the
Makefile directly — they are plain `uv run` / `uvx` commands with no make-specific
logic beyond the `GENERATED_FILES` list.

### Testing Strategy

**Tests are parametrized to run against multiple backends (Pyright, Pyrefly, ty, and Zuban).**

**Process Pool Tests (`tests/test_pool.py`)**
- Direct `LSPProcessPool` testing with generic interface
- Parametrized fixtures for testing Pyright, Pyrefly, ty, and Zuban backends
- Comprehensive pool behavior testing (creation, recycling, limits, cleanup)
- Performance benchmarks comparing pooled vs non-pooled sessions
- Concurrent usage scenarios and idle process management

**Session Tests (`tests/test_session.py`)**
- Core consolidated Session class functionality
- Parametrized fixtures for testing Pyright, Pyrefly, ty, and Zuban backends
- Integration testing with actual language servers (diagnostics, hover, completion)
- Dynamic environment testing with temporary directories
- Backend-agnostic tests that validate common LSP operations
- Backend-specific tests for unique configuration options (e.g., ty's nested config, Pyrefly's search_path)

### Dependencies

**Runtime:**
- `tomlkit>=0.13.3` - format-preserving TOML for Pyrefly, ty, and Zuban configuration serialization (Zuban edits the user's own `pyproject.toml`, so comments and layout must survive)

**Development:** uv-managed dependencies in `pyproject.toml`
- `pytest`, `pytest-asyncio`, `pytest-cov` for testing
- `datamodel-code-generator` for type generation
- `httpx` for schema downloading
- `rich` for the example scripts' console output

**Note:** Previously a zero-dependency library. Added a single TOML dependency for the Pyrefly, ty, and Zuban backends — `tomli-w` originally, replaced by `tomlkit` in v0.22.1 so Zuban's edit of `pyproject.toml` preserves the rest of the file.

### Examples

The `examples/` directory contains demo scripts showing library usage:
- `pyrefly_diagnostics_completion.py`: Diagnostics + completion walkthrough, run against Pyrefly then Pyright
- `pyrefly_circular_imports.py`: Cross-package circular-import hover behavior, run against Pyrefly then Pyright
- `extract_semantic_legends.py`: Dumps each backend's semantic-token legend as markdown for `docs/SEMANTIC_TOKENS.md`

### Important Notes

- Always prefix test commands with `uv run`
- **Before committing**: Run tests (`uv run pytest`), type checking (`uvx pyright`), and linting (`uvx ruff check .`) - CI will fail if any have errors
- `pyrefly`, `ty`, and `zuban` install into `.venv` via the matching extras, so `uv run pytest` finds them; `pyright-langserver` must be installed separately (needs Node)
- Type generation requires Python 3.12+ for modern TypedDict features
- Generated types should not be manually edited - regenerate from schemas
- Pyrefly, ty, and Zuban each ship a `KNOWN_LIMITATIONS.md` documenting backend-specific behaviors (Pyright has none)

### Architecture Design Patterns

**Backend Pattern**: LSP server integrations use the `LSPBackend` protocol to separate backend-specific logic (configuration formats, command-line arguments, capabilities) from common session management. This enables:
- Code reuse across different LSP implementations
- Easy addition of new LSP backends
- Consistent API while supporting diverse configuration needs
- Testable isolation of backend-specific behavior

**Lifecycle State Pattern**: Model an object's semantic lifecycle explicitly instead of making required collaborators optional. Keep dependencies such as a session's process and pool non-optional, revoke access through one typed guard when the lifecycle closes, and raise an explicit runtime error for invalid post-close use. This preserves strong internal invariants and avoids spreading `None` checks through otherwise-valid operations.
