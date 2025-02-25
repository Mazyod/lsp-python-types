import keyword
from enum import Enum
from typing import Literal

from ..lsp_schema import Enumeration, EnumerationEntry
from .helpers import capitalize, format_comment, indentation

ENUM_OVERRIDES: dict[str, Literal["StrEnum", "IntFlag"]] = {
    "CodeActionKind": "StrEnum",
    "DocumentDiagnosticReportKind": "StrEnum",
    "FailureHandlingKind": "StrEnum",
    "FileOperationPatternKind": "StrEnum",
    "FoldingRangeKind": "StrEnum",
    "LanguageKind": "StrEnum",
    "MarkupKind": "StrEnum",
    "MonikerKind": "StrEnum",
    "PositionEncodingKind": "StrEnum",
    "ResourceOperationKind": "StrEnum",
    "SemanticTokenModifiers": "StrEnum",
    "SemanticTokenTypes": "StrEnum",
    "TokenFormat": "StrEnum",
    "TraceValue": "StrEnum",
    "UniquenessLevel": "StrEnum",
    "WatchKind": "IntFlag",
}


class EnumKind(Enum):
    Number = 1
    String = 2


def format_enumeration_values(values: list[EnumerationEntry], kind: EnumKind) -> str:
    result: list[str] = []
    for v in values:
        key = capitalize(v["name"])
        if keyword.iskeyword(key):
            print(f"Conflict with {key} keyword, fallback to {key}_")
            key += "_"
        value = f"'{v['value']}'" if kind == EnumKind.String else v["value"]
        documentation = format_comment(v.get("documentation"), indentation)
        if documentation:
            documentation = "\n" + documentation

        result.append(f"{key} = {value}{documentation}")

    return f"\n{indentation}".join(result)


def generate_enumerations(enumerations: list[Enumeration]) -> list[str]:
    def toString(enumeration: Enumeration) -> str:
        result = ""
        symbol_name = enumeration["name"]
        documentation = format_comment(enumeration.get("documentation"), indentation)
        kind = (
            EnumKind.String
            if enumeration["type"]["name"] == "string"
            else EnumKind.Number
        )
        enum_class_override = ENUM_OVERRIDES.get(symbol_name)
        enum_class = enum_class_override or (
            "Enum" if kind == EnumKind.String else "IntEnum"
        )
        values = format_enumeration_values(enumeration["values"], kind)
        result += f"class {symbol_name}({enum_class}):\n"
        if documentation:
            result += f"{documentation}\n"
        result += f"{indentation}" + values
        return result

    return [toString(enumeration) for enumeration in enumerations]
