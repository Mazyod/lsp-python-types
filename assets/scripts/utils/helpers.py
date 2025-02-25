import keyword
from enum import Enum
from typing import Any, TypedDict, Union

from ..lsp_schema import BaseType, MapKeyType, Property, Type

indentation = "    "


def capitalize(text: str) -> str:
    return text[0].upper() + text[1:]


def format_comment(text: str | None, indent: str = "") -> str:
    if text:
        lines = text.splitlines(keepends=True)
        lines = lines[:1] + [
            line if line.isspace() else f"{indent}{line}" for line in lines[1:]
        ]
        text = "".join(lines)
    return indent + f'"""{text}"""' if text else ""


new_literal_structures: set[str] = set()


class SymbolNameTracker:
    symbols = {
        # key: symbol name
        # value: symbol count
    }

    @classmethod
    def get_symbol_id(cls, symbol_name: str):
        count = SymbolNameTracker.symbols.get(symbol_name) or 1
        SymbolNameTracker.symbols[symbol_name] = count + 1
        return count

    @classmethod
    def clear(cls):
        SymbolNameTracker.symbols.clear()


def get_new_literal_structures() -> list[str]:
    return sorted(new_literal_structures)


def reset_new_literal_structures() -> None:
    global new_literal_structures
    new_literal_structures.clear()
    SymbolNameTracker.clear()


class StructureKind(Enum):
    Class = 1
    Function = 2


class FormatTypeContext(TypedDict):
    root_symbol_name: str


def format_type(
    type: Type, context: FormatTypeContext, preferred_structure_kind: StructureKind
) -> str:
    result = "Any"

    match type["kind"]:
        case "base":
            return format_base_types(type)
        case "reference":
            literal_symbol_name = type["name"]
            return f"'{literal_symbol_name}'"
        case "array":
            literal_symbol_name = format_type(
                type["element"], context, preferred_structure_kind
            )
            return f"list[{literal_symbol_name}]"
        case "map":
            key = format_base_types(type["key"])
            value = format_type(
                type["value"], {"root_symbol_name": key}, preferred_structure_kind
            )
            return f"Mapping[{key}, {value}]"
        case "and":
            pass
        case "or":
            tuple = []
            for item in type["items"]:
                tuple.append(format_type(item, context, preferred_structure_kind))
            return f"Union[{', '.join(tuple)}]"
        case "tuple":
            tuple = []
            for item in type["items"]:
                tuple.append(format_type(item, context, preferred_structure_kind))
            return f"list[Union[{', '.join(tuple)}]]"
        case "literal":
            if not type["value"]["properties"]:
                return "dict"
            root_symbol_name = capitalize(context["root_symbol_name"])
            literal_symbol_name = f"__{root_symbol_name}_Type"
            symbol_id = SymbolNameTracker.get_symbol_id(literal_symbol_name)
            literal_symbol_name += f"_{symbol_id}"
            properties = get_formatted_properties(
                type["value"]["properties"], root_symbol_name, preferred_structure_kind
            )
            if preferred_structure_kind == StructureKind.Function:
                formatted_properties = format_dict_properties(properties)
                new_literal_structures.add(f"""
{literal_symbol_name} = TypedDict('{literal_symbol_name}', {{
{indentation}{formatted_properties}
}})
""")
            else:
                formatted_properties = format_class_properties(properties)
                new_literal_structures.add(f"""
class {literal_symbol_name}(TypedDict):
{indentation}{formatted_properties or "pass"}
""")
            return f"'{literal_symbol_name}'"
        case "stringLiteral" | "integerLiteral" | "booleanLiteral":
            return f"Literal['{type['value']}']"

    return result


def format_base_types(base_type: Union[BaseType, MapKeyType]):
    match base_type["name"]:
        case "integer":
            return "int"
        case "uinteger":
            return "Uint"
        case "decimal":
            return "float"
        case "string":
            return "str"
        case "boolean":
            return "bool"
        case "null":
            return "None"

    return f"'{base_type['name']}'"


class FormattedProperty(TypedDict):
    name: str
    value: Any
    documentation: str


def get_formatted_properties(
    properties: list[Property],
    root_symbol_name,
    preferred_structure_kind: StructureKind,
) -> list[FormattedProperty]:
    result: list[FormattedProperty] = []
    for p in properties:
        key = p["name"]
        value = format_type(
            p["type"],
            {"root_symbol_name": root_symbol_name + "_" + key},
            preferred_structure_kind,
        )
        if p.get("optional"):
            value = f"NotRequired[{value}]"
        documentation = p.get("documentation") or ""
        result.append({"name": key, "value": value, "documentation": documentation})

    return result


def has_invalid_property_name(properties: list[Property]):
    return any(keyword.iskeyword(p["name"]) for p in properties)


def format_class_properties(properties: list[FormattedProperty]) -> str:
    result: list[str] = []
    for p in properties:
        line = f"{p['name']}: {p['value']}"
        comment = format_comment(p["documentation"], indentation)
        if comment:
            line += f"\n{comment}"
        result.append(line)
    return f"\n{indentation}".join(result)


def format_dict_properties(properties: list[FormattedProperty]) -> str:
    result: list[str] = []
    for p in properties:
        documentation = p.get("documentation")
        formatted_documentation = ""
        if documentation:
            formatted_documentation = documentation.replace("\n", f"\n{indentation}# ")
            formatted_documentation = f"# {formatted_documentation}\n{indentation}"
        result.append(f"{formatted_documentation}'{p['name']}': {p['value']},")
    return f"\n{indentation}".join(result)
