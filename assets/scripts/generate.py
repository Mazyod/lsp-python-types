#!/usr/bin/env python3
import json

from pathlib import Path
from .lsp_schema import MetaModel
from .utils.generate_enumerations import generate_enumerations
from .utils.generate_structures import generate_structures
from .utils.generate_type_aliases import generate_type_aliases
from .utils.generate_requests import generate_requests
from .utils.generate_notifications import generate_notifications
from .utils.helpers import (
    get_new_literal_structures,
    reset_new_literal_structures,
    indentation,
)


def generate_python_types(lsp_json: MetaModel, output: Path):
    specification_version = lsp_json["metaData"]["version"]

    generated_enums = "\n\n\n".join(generate_enumerations(lsp_json["enumerations"]))
    generated_type_aliases = "\n".join(generate_type_aliases(lsp_json["typeAliases"]))
    generated_structs = "\n\n\n".join(generate_structures(lsp_json["structures"]))
    generated_literals = "\n".join(get_new_literal_structures())

    content = f"""\
from __future__ import annotations

# Generated code.
# DO NOT EDIT.
# LSP v{specification_version}

from typing import Any, Literal, Mapping, TypedDict, Union, NotRequired
from enum import IntEnum, IntFlag, StrEnum


URI = str
DocumentUri = str
Uint = int
RegExp = str


{generated_enums}

{generated_type_aliases}


{generated_structs}

{generated_literals}"""

    # Remove trailing spaces.
    lines = content.split("\n")
    lines = [line.rstrip() for line in lines]
    content = "\n".join(lines)

    output.write_text(content)


def generate_python_requests(lsp_json: MetaModel, output: Path):
    specification_version = lsp_json["metaData"]["version"]

    generated_requests = "\n".join(generate_requests(lsp_json["requests"]))
    generated_notifs = "\n".join(generate_notifications(lsp_json["notifications"]))

    content = f"""from __future__ import annotations

# Generated code.
# DO NOT EDIT.
# LSP v{specification_version}

from typing import Any, Awaitable, Callable, Union
from . import types


RequestDispatcher = Callable[[str, types.LSPAny], Awaitable[Any]]


class RequestFunctions:
{indentation}def __init__(self, dispatcher: RequestDispatcher):
{indentation}{indentation}self.dispatcher = dispatcher

{generated_requests}


NotificationDispatcher = Callable[[str, types.LSPAny], Awaitable[None]]
NotificationHandler = Callable[[str, float | None], Awaitable[Union[types.LSPAny]]]


class NotificationFunctions:
{indentation}def __init__(self, dispatcher: NotificationDispatcher, on_notification: NotificationHandler):
{indentation}{indentation}self.dispatcher = dispatcher
{indentation}{indentation}self.on_notification = on_notification

{generated_notifs}"""

    output.write_text(content)


if __name__ == "__main__":
    lsp_json_path = Path("./assets/lsprotocol/lsp.json")
    base_path = Path("./lsp_types")

    with lsp_json_path.open() as file:
        lsp_json: MetaModel = json.load(file)

    reset_new_literal_structures()

    generate_python_types(lsp_json, base_path / "types.py")
    generate_python_requests(lsp_json, base_path / "requests.py")
