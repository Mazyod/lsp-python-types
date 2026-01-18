#!/usr/bin/env python3
"""
Mock LSP Server for testing failure scenarios.

This module provides a configurable mock LSP server that can be launched as a subprocess
and used to test timeout, error, and malformed response handling in the LSP client.

Usage:
    # Normal mode - responds to all requests with default responses
    python mock_lsp_server.py

    # Hang on a specific method (for timeout testing)
    python mock_lsp_server.py --hang-on textDocument/hover

    # Return error for a specific method
    python mock_lsp_server.py --error-on textDocument/hover --error-code -32600 --error-message "Test error"

    # Return malformed JSON-RPC for a specific method
    python mock_lsp_server.py --malformed-on textDocument/hover
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


class MockLSPServer:
    """A minimal mock LSP server for testing failure scenarios."""

    def __init__(
        self,
        hang_on: str | None = None,
        error_on: str | None = None,
        error_code: int = -32600,
        error_message: str = "Mock error",
        malformed_on: str | None = None,
    ):
        self.hang_on = hang_on
        self.error_on = error_on
        self.error_code = error_code
        self.error_message = error_message
        self.malformed_on = malformed_on
        self._initialized = False

    def read_message(self) -> dict[str, Any] | None:
        """Read a JSON-RPC message from stdin with Content-Length header."""
        # Read headers
        content_length = 0
        while True:
            line = sys.stdin.buffer.readline()
            if not line or line == b"\r\n":
                break
            if line.startswith(b"Content-Length: "):
                content_length = int(line.split(b":")[1].strip())

        if content_length == 0:
            return None

        # Read body
        body = sys.stdin.buffer.read(content_length)
        return json.loads(body.decode("utf-8"))

    def write_message(self, message: dict[str, Any]) -> None:
        """Write a JSON-RPC message to stdout with Content-Length header."""
        body = json.dumps(message).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n"
        sys.stdout.buffer.write(header.encode("utf-8"))
        sys.stdout.buffer.write(body)
        sys.stdout.buffer.flush()

    def write_malformed(self) -> None:
        """Write an intentionally malformed response."""
        # Write invalid JSON that looks like it has correct headers
        malformed = b"not valid json {"
        header = f"Content-Length: {len(malformed)}\r\n\r\n"
        sys.stdout.buffer.write(header.encode("utf-8"))
        sys.stdout.buffer.write(malformed)
        sys.stdout.buffer.flush()

    def handle_request(self, message: dict[str, Any]) -> None:
        """Handle an incoming request message."""
        method = message.get("method", "")
        request_id = message.get("id")

        # Check if this is a notification (no id)
        is_notification = request_id is None

        # Handle configured behaviors
        if method == self.hang_on:
            # Don't respond - simulate hang/timeout
            return

        if method == self.malformed_on and not is_notification:
            self.write_malformed()
            return

        if method == self.error_on and not is_notification:
            self.write_message(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": self.error_code,
                        "message": self.error_message,
                    },
                }
            )
            return

        # Handle standard LSP methods
        if method == "initialize" and request_id is not None:
            self._handle_initialize(request_id)
        elif method == "initialized":
            self._initialized = True
            # No response for notifications
        elif method == "shutdown" and request_id is not None:
            self._handle_shutdown(request_id)
        elif method == "exit":
            sys.exit(0)
        elif not is_notification and request_id is not None:
            # Default response for unknown requests
            self._handle_default(request_id, method)

    def _handle_initialize(self, request_id: int | str) -> None:
        """Handle the initialize request."""
        self.write_message(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "capabilities": {
                        "textDocumentSync": 1,
                        "hoverProvider": True,
                        "completionProvider": {},
                    },
                    "serverInfo": {
                        "name": "mock-lsp-server",
                        "version": "1.0.0",
                    },
                },
            }
        )

    def _handle_shutdown(self, request_id: int | str) -> None:
        """Handle the shutdown request."""
        self.write_message({"jsonrpc": "2.0", "id": request_id, "result": None})

    def _handle_default(self, request_id: int | str, method: str) -> None:
        """Handle unknown requests with empty/null response."""
        self.write_message({"jsonrpc": "2.0", "id": request_id, "result": None})

    def run(self) -> None:
        """Main loop: read and handle messages until exit."""
        while True:
            message = self.read_message()
            if message is None:
                break
            self.handle_request(message)


def main():
    parser = argparse.ArgumentParser(description="Mock LSP Server for testing")
    parser.add_argument(
        "--hang-on",
        type=str,
        help="Method to hang on (don't respond)",
    )
    parser.add_argument(
        "--error-on",
        type=str,
        help="Method to return an error for",
    )
    parser.add_argument(
        "--error-code",
        type=int,
        default=-32600,
        help="Error code to return (default: -32600)",
    )
    parser.add_argument(
        "--error-message",
        type=str,
        default="Mock error",
        help="Error message to return",
    )
    parser.add_argument(
        "--malformed-on",
        type=str,
        help="Method to return malformed JSON-RPC for",
    )

    args = parser.parse_args()

    server = MockLSPServer(
        hang_on=args.hang_on,
        error_on=args.error_on,
        error_code=args.error_code,
        error_message=args.error_message,
        malformed_on=args.malformed_on,
    )
    server.run()


if __name__ == "__main__":
    main()
