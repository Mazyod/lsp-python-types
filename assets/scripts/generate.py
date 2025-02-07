#!/usr/bin/env python3
import json

from typing import Dict, Literal  # noqa (for type hint comments)
from .lsp_schema import MetaModel
from .utils.generate_enumerations import generate_enumerations
from .utils.generate_structures import generate_structures
from .utils.generate_type_aliases import generate_type_aliases
from .utils.helpers import get_new_literal_structures, reset_new_literal_structures, StructureKind


ENUM_OVERRIDES = {
    'CodeActionKind': 'StrEnum',
    'DocumentDiagnosticReportKind': 'StrEnum',
    'FailureHandlingKind': 'StrEnum',
    'FileOperationPatternKind': 'StrEnum',
    'FoldingRangeKind': 'StrEnum',
    'LanguageKind': 'StrEnum',
    'MarkupKind': 'StrEnum',
    'MonikerKind': 'StrEnum',
    'PositionEncodingKind': 'StrEnum',
    'ResourceOperationKind': 'StrEnum',
    'SemanticTokenModifiers': 'StrEnum',
    'SemanticTokenTypes': 'StrEnum',
    'TokenFormat': 'StrEnum',
    'TraceValue': 'StrEnum',
    'UniquenessLevel': 'StrEnum',
    'WatchKind': 'IntFlag'
}  # type: Dict[str, Literal['StrEnum', 'IntFlag']]


def generate(preferred_structure_kind: StructureKind, output: str) -> None:
    reset_new_literal_structures()

    with open('./assets/lsprotocol/lsp.json') as file:
        lsp_json: MetaModel = json.load(file)
        specification_version = lsp_json.get('metaData')['version']

        content = "\n".join([
            "# Code generated. DO NOT EDIT.",
            f"# LSP v{specification_version}\n",
            "from typing import Dict, List, Literal, TypedDict, Union, NotRequired",
            "from enum import IntEnum, IntFlag, StrEnum\n\n",
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


generate(preferred_structure_kind=StructureKind.Class, output="./lsp_types/types.py")
# generate(preferred_structure_kind=StructureKind.Function, output="./lsp/types_sublime_text_33.py")
