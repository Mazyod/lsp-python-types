# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

Always use `uv` for Python operations:

```bash
# Run tests
uv run pytest                                  # All tests
uv run pytest tests/test_pool.py               # Generic pool tests
uv run pytest tests/test_pyright/              # Pyright-specific tests  
uv run pytest tests/test_pool.py::TestLSPProcessPool::test_name -v  # Single pool test

# Generate latest LSP types (full pipeline)
make generate-latest-types                     # Downloads schemas + generates all types

# Individual generation steps
make download-schemas                          # Download latest LSP schemas
make generate-lsp-schema                       # Generate main LSP types
make generate-pyright-schema                   # Generate Pyright config types
make generate-types                            # Generate final type definitions
```

## Architecture Overview

This is a zero-dependency Python library providing typed LSP (Language Server Protocol) interfaces with optional process management.

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

**Session Protocol (`lsp_types/session.py`)**
- `Session`: Protocol defining standard LSP session interface
- Abstract interface for `shutdown()`, `update_code()`, `get_diagnostics()`, etc.
- Implemented by language-specific sessions like `PyrightSession`

**Generic Process Pooling (`lsp_types/pool.py`)**
- `LSPProcessPool`: Language-server agnostic process pooling for performance optimization
- `PooledLSPProcess`: Wrapper for `LSPProcess` with recycling state management
- Reusable across different LSP implementations (not just Pyright)
- Handles process lifecycle: creation, reuse, idle cleanup, and shutdown

**Pyright Integration (`lsp_types/pyright/`)**
- `PyrightSession`: High-level Pyright LSP session implementation
- `config_schema.py`: Auto-generated Pyright configuration types
- **Key Design**: PyrightSession uses generic `LSPProcessPool` for session reuse

### Type Generation Pipeline

**Schema Sources:**
- `assets/lsprotocol/lsp.schema.json`: Official LSP protocol schema
- `assets/lsps/pyright.schema.json`: Pyright-specific configuration schema

**Generation Process:**
1. `download_schemas.py`: Fetches latest schemas from upstream
2. `datamodel-codegen`: Converts JSON schema to TypedDict definitions
3. `postprocess_schema.py`: Applies fixes for codegen limitations
4. `generate.py`: Orchestrates final type file generation with utilities in `assets/scripts/utils/`

### Testing Strategy

**Process Pool Tests**
- `tests/test_pool.py`: Direct `LSPProcessPool` testing with generic interface
- `tests/test_pyright/test_session_pool.py`: Pool integration testing through Pyright sessions
- Comprehensive pool behavior testing (creation, recycling, limits, cleanup)
- Performance benchmarks comparing pooled vs non-pooled sessions
- Concurrent usage scenarios and idle process management

**Session Tests (`tests/test_pyright/test_pyright_session.py`)**
- Core LSP functionality testing (diagnostics, hover, completion)
- Integration testing with actual Pyright language server

### Dependencies

**Runtime:** Zero dependencies (core design goal)
**Development:** uv-managed dependencies in `pyproject.toml`
- `pytest` with async support for testing
- `datamodel-code-generator` for type generation
- `httpx` for schema downloading

### Important Notes

- Always prefix test commands with `uv run`
- Pool tests require `pyright-langserver` binary available in PATH
- Type generation requires Python 3.11+ for modern TypedDict features
- Generated types should not be manually edited - regenerate from schemas
