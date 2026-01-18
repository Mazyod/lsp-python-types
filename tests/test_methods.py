"""
Tests for LSP method enums.
"""

from lsp_types import methods


def test_request_enum_values():
    """Verify request enum values match expected LSP method strings"""
    assert methods.Request.INITIALIZE == "initialize"
    assert methods.Request.SHUTDOWN == "shutdown"
    assert methods.Request.TEXT_DOCUMENT_HOVER == "textDocument/hover"
    assert methods.Request.TEXT_DOCUMENT_COMPLETION == "textDocument/completion"
    assert methods.Request.TEXT_DOCUMENT_DEFINITION == "textDocument/definition"
    assert methods.Request.TEXT_DOCUMENT_DIAGNOSTIC == "textDocument/diagnostic"


def test_notification_enum_values():
    """Verify notification enum values match expected LSP method strings"""
    assert methods.Notification.INITIALIZED == "initialized"
    assert methods.Notification.EXIT == "exit"
    assert methods.Notification.TEXT_DOCUMENT_DID_OPEN == "textDocument/didOpen"
    assert methods.Notification.TEXT_DOCUMENT_DID_CHANGE == "textDocument/didChange"
    assert methods.Notification.TEXT_DOCUMENT_DID_CLOSE == "textDocument/didClose"


def test_enum_string_compatibility():
    """Verify enums work exactly like strings"""
    method = methods.Request.TEXT_DOCUMENT_HOVER

    # StrEnum values are strings
    assert isinstance(method, str)

    # String equality works
    assert method == "textDocument/hover"

    # String operations work
    assert f"Method: {method}" == "Method: textDocument/hover"
    assert method.startswith("textDocument/")


def test_all_key_request_methods_defined():
    """Verify all commonly used request methods are defined"""
    # Core lifecycle
    assert hasattr(methods.Request, "INITIALIZE")
    assert hasattr(methods.Request, "SHUTDOWN")

    # Document operations
    assert hasattr(methods.Request, "TEXT_DOCUMENT_HOVER")
    assert hasattr(methods.Request, "TEXT_DOCUMENT_COMPLETION")
    assert hasattr(methods.Request, "TEXT_DOCUMENT_DEFINITION")
    assert hasattr(methods.Request, "TEXT_DOCUMENT_REFERENCES")
    assert hasattr(methods.Request, "TEXT_DOCUMENT_RENAME")
    assert hasattr(methods.Request, "TEXT_DOCUMENT_FORMATTING")
    assert hasattr(methods.Request, "TEXT_DOCUMENT_DIAGNOSTIC")

    # Semantic tokens
    assert hasattr(methods.Request, "TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL")


def test_all_key_notification_methods_defined():
    """Verify all commonly used notification methods are defined"""
    # Core lifecycle
    assert hasattr(methods.Notification, "INITIALIZED")
    assert hasattr(methods.Notification, "EXIT")

    # Document notifications
    assert hasattr(methods.Notification, "TEXT_DOCUMENT_DID_OPEN")
    assert hasattr(methods.Notification, "TEXT_DOCUMENT_DID_CHANGE")
    assert hasattr(methods.Notification, "TEXT_DOCUMENT_DID_CLOSE")
    assert hasattr(methods.Notification, "TEXT_DOCUMENT_DID_SAVE")
