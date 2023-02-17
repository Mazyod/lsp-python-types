#!/usr/bin/env python3
import json

from lsp_schema import MetaModel
from typing import Dict, Literal
from utils.generate_enumerations import generate_enumerations
from utils.generate_structures import generate_structures
from utils.generate_type_aliases import generate_type_aliases
from utils.generate_requests import generate_requests
from utils.generate_notifications import generate_notifications
from utils.helpers import get_new_literal_structures, reset_new_literal_structures, StructureKind, indentation


ENUM_OVERRIDES = {
    'CodeActionKind': 'StrEnum',
    'WatchKind': 'IntFlag',
}  # type: Dict[str, Literal['StrEnum', 'IntFlag']]


def generate(preferred_structure_kind: StructureKind, output: str) -> None:
    reset_new_literal_structures()

    with open('./lsprotocol/lsp.json') as file:
        lsp_json: MetaModel = json.load(file)
        specification_version = lsp_json.get('metaData')['version']

        content = "\n".join([
            "# Code generated. DO NOT EDIT.",
            f"# LSP v{specification_version}\n",
            "from typing_extensions import NotRequired",
            "from typing import Dict, List, Literal, TypedDict, Union",
            "from enum import Enum, IntEnum, IntFlag\n\n",
            "import sys",
            "if sys.version_info >= (3, 11, 0):",
            f"{indentation}from enum import StrEnum",
            "else:",
            f"{indentation}StrEnum = Enum",
            "URI = str",
            "DocumentUri = str",
            "Uint = int",
            "RegExp = str",
        ])

        content += '\n\n\n'
        content += '\n\n\n'.join(generate_enumerations(lsp_json['enumerations'], ENUM_OVERRIDES))
        content += '\n\n'
        content += '\n'.join(generate_type_aliases(lsp_json['typeAliases'], preferred_structure_kind))
        content += '\n\n\n'
        content += '\n\n\n'.join(generate_structures(lsp_json['structures'], preferred_structure_kind))
        content += '\n\n'
        content += '\n'.join(get_new_literal_structures())

        # Remove trailing spaces.
        lines = content.split('\n')
        lines = [line.rstrip() for line in lines]
        content = '\n'.join(lines)

        with open(output, "w") as new_file:
            new_file.write(content)


generate(preferred_structure_kind=StructureKind.Class, output="./lsp_types.py")
generate(preferred_structure_kind=StructureKind.Function, output="./lsp_types_sublime_text_33.py")


def generate_req(output) -> None:
    content = f"""# Code generated. DO NOT EDIT.
import lsp_types
from typing import List, Union


class LspRequest:
{indentation}def __init__(self, send_request):
{indentation}{indentation}self.send_request = send_request\n\n"""

    with open('./lsprotocol/lsp.json') as file:
        lsp_json: MetaModel = json.load(file)
        content += '\n'.join(generate_requests(lsp_json['requests']))
        content += f"""\n\nclass LspNotification:
{indentation}def __init__(self, send_notification):
{indentation}{indentation}self.send_notification = send_notification\n\n"""
        content += '\n'.join(generate_notifications(lsp_json['notifications']))


        with open(output, "w") as new_file:
                new_file.write(content)


generate_req('./lsp_requests.py')
