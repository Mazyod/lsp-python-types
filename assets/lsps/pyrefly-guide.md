# Pyrefly: A Developer's Guide to Programmatic Usage and LSP Integration

This guide documents practical insights gained from implementing a proof of concept with Pyrefly, Facebook's fast Python type checker and Language Server Protocol (LSP) server written in Rust.

## Overview

Pyrefly is a modern alternative to traditional Python type checkers like mypy, offering:

- **Performance**: Written in Rust for speed on large codebases
- **LSP Support**: Built-in Language Server Protocol implementation
- **Editor Integration**: Works with VS Code, Neovim, Emacs, Vim, and other LSP-compatible editors
- **Type Checking**: Advanced static analysis with comprehensive diagnostics

## Command Line Interface

### Basic Usage

Pyrefly provides several commands accessible via its CLI:

```bash
# Type check a single file
pyrefly check main.py

# Type check entire project
pyrefly check

# Start LSP server
pyrefly lsp

# Check a code snippet
pyrefly snippet "def hello(name: str) -> str: return f'Hello {name}'"

# Initialize configuration
pyrefly init

# Display configuration
pyrefly dump-config
```

### Key CLI Options

- `--verbose`: Enable detailed logging
- `--threads N`: Control parallelization (0 = auto)
- `--color`: Control colored output (auto/always/never)

## LSP Server Implementation

### Starting the LSP Server

```bash
# Basic LSP server
pyrefly lsp

# With verbose logging
pyrefly lsp --verbose

# With specific indexing mode
pyrefly lsp --indexing-mode lazy-non-blocking-background
```

### Indexing Modes

Pyrefly supports different indexing strategies:

- `none`: Disable indexing (disables find-refs, etc.)
- `lazy-non-blocking-background`: Index in background thread (default)
- `lazy-blocking`: Index in main thread (blocks IDE services)

### LSP Communication Protocol

The LSP server communicates via JSON-RPC over stdin/stdout. Here's the basic flow:

#### 1. Initialize Connection

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "processId": 12345,
    "rootUri": "file:///path/to/project",
    "capabilities": {
      "textDocument": {
        "hover": {"contentFormat": ["markdown", "plaintext"]},
        "completion": {},
        "definition": {},
        "references": {}
      }
    }
  }
}
```

#### 2. Send Initialized Notification

```json
{
  "jsonrpc": "2.0",
  "method": "initialized",
  "params": {}
}
```

#### 3. Open Document

```json
{
  "jsonrpc": "2.0",
  "method": "textDocument/didOpen",
  "params": {
    "textDocument": {
      "uri": "file:///path/to/file.py",
      "languageId": "python",
      "version": 1,
      "text": "def hello(name: str) -> str:\n    return f'Hello {name}'"
    }
  }
}
```

#### 4. Request Features

```json
// Hover information
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "textDocument/hover",
  "params": {
    "textDocument": {"uri": "file:///path/to/file.py"},
    "position": {"line": 0, "character": 4}
  }
}

// Code completion
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "textDocument/completion",
  "params": {
    "textDocument": {"uri": "file:///path/to/file.py"},
    "position": {"line": 1, "character": 10}
  }
}
```

### Python LSP Client Implementation

Here's a minimal Python client for interacting with Pyrefly LSP:

```python
import subprocess
import json
import os

class PyreflyLSPClient:
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.process = None
    
    def start_server(self):
        """Start Pyrefly LSP server process."""
        self.process = subprocess.Popen(
            ["pyrefly", "lsp", "--verbose"],
            cwd=self.project_root,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0
        )
    
    def send_message(self, message: dict):
        """Send JSON-RPC message to LSP server."""
        content = json.dumps(message)
        content_length = len(content.encode('utf-8'))
        
        # LSP requires Content-Length header
        full_message = f"Content-Length: {content_length}\r\n\r\n{content}"
        
        self.process.stdin.write(full_message)
        self.process.stdin.flush()
    
    def initialize(self):
        """Initialize LSP connection."""
        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "processId": os.getpid(),
                "rootUri": f"file://{self.project_root}",
                "capabilities": {
                    "textDocument": {
                        "hover": {"contentFormat": ["markdown"]},
                        "completion": {},
                        "definition": {},
                        "references": {}
                    }
                }
            }
        }
        
        self.send_message(init_msg)
        
        # Send initialized notification
        self.send_message({
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        })
```

## Programmatic Diagnostics

### Running Type Checks Programmatically

```python
import subprocess
import json

def run_pyrefly_check(file_path: str) -> tuple[int, str, str]:
    """Run Pyrefly type check and return results."""
    result = subprocess.run(
        ["pyrefly", "check", file_path],
        capture_output=True,
        text=True
    )
    
    return result.returncode, result.stdout, result.stderr

# Usage
exit_code, stdout, stderr = run_pyrefly_check("main.py")
if exit_code == 0:
    print("No type errors found")
else:
    print(f"Type errors detected:\n{stderr}")
```

### Parsing Diagnostic Output

Pyrefly outputs diagnostics in a structured format. Here's how to parse them:

```python
import re
from typing import List, Dict, Any

def parse_pyrefly_diagnostics(stderr: str) -> List[Dict[str, Any]]:
    """Parse Pyrefly diagnostic output into structured data."""
    diagnostics = []
    
    # Pattern for Pyrefly error messages
    error_pattern = r'(.+):(\d+):(\d+): (.+)'
    
    for line in stderr.strip().split('\n'):
        if 'ERROR' in line or 'WARN' in line:
            match = re.search(error_pattern, line)
            if match:
                diagnostics.append({
                    'file': match.group(1),
                    'line': int(match.group(2)),
                    'column': int(match.group(3)),
                    'message': match.group(4),
                    'severity': 'error' if 'ERROR' in line else 'warning'
                })
    
    return diagnostics
```

## Configuration

### Project Configuration

Pyrefly looks for configuration in `pyrefly.toml` at the project root. However, during testing, many standard configuration options weren't recognized, suggesting the configuration format is still evolving.

### Working Configuration Approach

Instead of relying on configuration files, use command-line options for consistent behavior:

```bash
# Recommended approach
pyrefly lsp --verbose --threads 4
```

### Environment Variables

Pyrefly respects these environment variables:

- `PYREFLY_THREADS`: Number of threads for parallelization
- `PYREFLY_COLOR`: Color output control
- `PYREFLY_VERBOSE`: Enable verbose logging

## Editor Integration Examples

### VS Code

Install the official Pyrefly extension from the marketplace, or configure manually:

```json
{
  "python.languageServer": "Pyrefly",
  "pyrefly.args": ["--verbose"]
}
```

### Neovim (with nvim-lspconfig)

```lua
require('lspconfig').pyrefly.setup{
  cmd = {"pyrefly", "lsp"},
  settings = {
    pyrefly = {
      -- Add any Pyrefly-specific settings here
    }
  }
}
```

### Emacs (with Eglot)

```elisp
(add-to-list 'eglot-server-programs 
             '(python-mode . ("pyrefly" "lsp")))
```

## Performance Considerations

### Indexing Strategy

Choose indexing mode based on your needs:

- **Development**: Use `lazy-non-blocking-background` for responsiveness
- **CI/Testing**: Use `lazy-blocking` for deterministic behavior
- **Large Projects**: Consider `none` if find-references isn't critical

### Threading

- Default (0) uses automatic thread detection
- Set to 1 for sequential execution
- Higher values can improve performance on large codebases

## Troubleshooting

### Common Issues

1. **Module Import Errors**: Ensure Pyrefly can find your Python environment
2. **LSP Connection Issues**: Check that stdin/stdout aren't being used by other processes
3. **Configuration Warnings**: Many config options may not be supported yet
4. **Performance**: Adjust indexing mode and thread count for your workflow

### Debugging LSP Communication

Enable verbose mode and monitor stderr for detailed protocol messages:

```bash
pyrefly lsp --verbose 2> lsp-debug.log
```

## Key Learnings

1. **Fast Performance**: Pyrefly is noticeably faster than traditional Python type checkers
2. **LSP-First Design**: Built from the ground up with LSP support in mind
3. **Minimal Configuration**: Works well with minimal setup, unlike some alternatives
4. **Active Development**: Configuration options and features are still evolving
5. **Editor Agnostic**: Works with any LSP-compatible editor
6. **Rust Performance**: Benefits from Rust's performance characteristics for large codebases

## Best Practices

1. Start with minimal configuration and add complexity as needed
2. Use verbose mode during development and debugging
3. Choose appropriate indexing mode for your workflow
4. Monitor performance with different thread settings
5. Keep the LSP server process isolated from your main application
6. Use programmatic access for CI/CD integration

## Resources

- [Pyrefly GitHub Repository](https://github.com/facebook/pyrefly)
- [Language Server Protocol Specification](https://microsoft.github.io/language-server-protocol/)
- [LSP Client Libraries](https://microsoft.github.io/language-server-protocol/implementors/sdks/)