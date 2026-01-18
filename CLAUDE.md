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
uvx pyright                                    # Run pyright type checker
uvx pyright lsp_types/                         # Check only library code
uvx pyright tests/                             # Check only test code

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
- `PooledLSPProcess`: Wrapper for `LSPProcess` with recycling state management
- Reusable across different LSP implementations (not just Pyright)
- Handles process lifecycle: creation, reuse, idle cleanup, and shutdown

**Backend Integrations**

**Pyright Integration (`lsp_types/pyright/`)**
- `backend.py`: `PyrightBackend` implementation for Pyright LSP server
- `config_schema.py`: Auto-generated Pyright configuration types
- **Key Design**: Uses consolidated `Session` class with `PyrightBackend` for specialization

**Pyrefly Integration (`lsp_types/pyrefly/`)**
- `backend.py`: `PyreflyBackend` implementation for Pyrefly LSP server (Facebook's Rust-based type checker)
- `config_schema.py`: Pyrefly configuration types (TypedDict with known fields)
- **Key Design**: Uses consolidated `Session` class with `PyreflyBackend` for specialization
- **Config Flexibility**: Supports arbitrary configuration fields via TOML serialization (using `tomli-w`)

**ty Integration (`lsp_types/ty/`)**
- `backend.py`: `TyBackend` implementation for ty LSP server (Astral's Rust-based type checker)
- `config_schema.py`: ty configuration types with nested sections (environment, src, rules, etc.)
- **Key Design**: Uses consolidated `Session` class with `TyBackend` for specialization
- **Config Format**: TOML (`ty.toml`) with nested sections and kebab-case keys
- **Known Limitation**: ty requires files to exist on disk (virtual documents not fully supported)
- **Documentation**: See `KNOWN_LIMITATIONS.md` in the ty package for details

### Type Generation Pipeline

**Schema Sources:**
- `assets/lsprotocol/lsp.schema.json`: Official LSP protocol schema
- `assets/lsps/pyright.schema.json`: Pyright-specific configuration schema
- `assets/lsps/pyrefly-guide.md`: Pyrefly configuration documentation (manually defined types)

**Generation Process:**
1. `download_schemas.py`: Fetches latest schemas from upstream
2. `datamodel-codegen`: Converts JSON schema to TypedDict definitions
3. `generate.py`: Orchestrates final type file generation with utilities in `assets/scripts/utils/`

### Testing Strategy

**Tests are parametrized to run against multiple backends (Pyright, Pyrefly, and ty).**

**Process Pool Tests (`tests/test_pool.py`)**
- Direct `LSPProcessPool` testing with generic interface
- Parametrized fixtures for testing Pyright, Pyrefly, and ty backends
- Comprehensive pool behavior testing (creation, recycling, limits, cleanup)
- Performance benchmarks comparing pooled vs non-pooled sessions
- Concurrent usage scenarios and idle process management

**Session Tests (`tests/test_session.py`)**
- Core consolidated Session class functionality
- Parametrized fixtures for testing Pyright, Pyrefly, and ty backends
- Integration testing with actual language servers (diagnostics, hover, completion)
- Dynamic environment testing with temporary directories
- Backend-agnostic tests that validate common LSP operations
- Backend-specific tests for unique configuration options (e.g., ty's nested config, Pyrefly's search_path)

### Dependencies

**Runtime:**
- `tomli-w>=1.0.0` - TOML writing support for Pyrefly and ty configuration serialization

**Development:** uv-managed dependencies in `pyproject.toml`
- `pytest` with async support for testing
- `datamodel-code-generator` for type generation
- `httpx` for schema downloading

**Note:** Previously a zero-dependency library. Added `tomli-w` to support TOML configuration for Pyrefly and ty backends.

### Examples

The `examples/` directory contains demo scripts showing library usage:
- `pyrefly_diagnostics_completion.py`: Demonstrates diagnostics and code completion with Pyrefly
- `pyrefly_circular_imports.py`: Example of detecting circular import issues

### Important Notes

- Always prefix test commands with `uv run`
- **Before committing**: Run tests (`uv run pytest`), type checking (`uvx pyright`), and linting (`uvx ruff check .`) - CI will fail if any have errors
- Pool tests require `pyright-langserver`, `pyrefly`, and/or `ty` binaries available in PATH
- Type generation requires Python 3.12+ for modern TypedDict features
- Generated types should not be manually edited - regenerate from schemas
- Each backend has a `KNOWN_LIMITATIONS.md` file documenting backend-specific behaviors

### Architecture Design Patterns

**Backend Pattern**: LSP server integrations use the `LSPBackend` protocol to separate backend-specific logic (configuration formats, command-line arguments, capabilities) from common session management. This enables:
- Code reuse across different LSP implementations
- Easy addition of new LSP backends
- Consistent API while supporting diverse configuration needs
- Testable isolation of backend-specific behavior
