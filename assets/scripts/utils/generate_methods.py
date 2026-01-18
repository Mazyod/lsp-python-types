import re
from pathlib import Path

from ..lsp_schema import MetaModel


def method_to_enum_name(method: str) -> str:
    """Convert an LSP method name to an enum member name.

    Examples:
        textDocument/hover -> TEXT_DOCUMENT_HOVER
        $/progress -> PROGRESS
        callHierarchy/incomingCalls -> CALL_HIERARCHY_INCOMING_CALLS
        textDocument/semanticTokens/full/delta -> TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL_DELTA
    """
    # Strip $/ prefix
    if method.startswith("$/"):
        method = method[2:]

    # Replace / with _
    method = method.replace("/", "_")

    # Convert camelCase to UPPER_SNAKE_CASE
    # Insert underscore before uppercase letters that follow lowercase letters
    result = re.sub(r"([a-z])([A-Z])", r"\1_\2", method)

    return result.upper()


def generate_methods(lsp_json: MetaModel, output_path: Path) -> None:
    """Generate LSP method enum classes from the LSP schema.

    Args:
        lsp_json: The parsed LSP JSON schema
        output_path: Path to write the generated Python file
    """
    specification_version = lsp_json["metaData"]["version"]

    # Collect request methods (client-to-server only)
    request_methods: list[tuple[str, str]] = []
    for request in lsp_json["requests"]:
        if request["messageDirection"] == "serverToClient":
            continue
        method = request["method"]
        enum_name = method_to_enum_name(method)
        request_methods.append((enum_name, method))

    # Sort by enum name for consistent output
    request_methods.sort(key=lambda x: x[0])

    # Collect notification methods (client-to-server or both)
    notification_methods: list[tuple[str, str]] = []
    for notification in lsp_json["notifications"]:
        direction = notification["messageDirection"]
        if direction == "serverToClient":
            continue
        method = notification["method"]
        enum_name = method_to_enum_name(method)
        notification_methods.append((enum_name, method))

    # Sort by enum name for consistent output
    notification_methods.sort(key=lambda x: x[0])

    # Generate enum members
    request_members = "\n".join(
        f'    {name} = "{value}"' for name, value in request_methods
    )
    notification_members = "\n".join(
        f'    {name} = "{value}"' for name, value in notification_methods
    )

    content = f'''\
from __future__ import annotations

# Generated code.
# DO NOT EDIT.
# LSP v{specification_version}

from enum import StrEnum


class Request(StrEnum):
    """LSP request method identifiers"""

{request_members}


class Notification(StrEnum):
    """LSP notification method identifiers"""

{notification_members}
'''

    output_path.write_text(content)
