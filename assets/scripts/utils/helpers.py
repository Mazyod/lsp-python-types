from enum import Enum
from typing import Any, List, Optional, Set, TypedDict, Union
from ..lsp_schema import _Type, BaseType, MapKeyType, Property
import keyword

indentation = "    "


def capitalize(text: str) -> str:
    return text[0].upper() + text[1:]


def format_comment(text: Optional[str], indent: str = "") -> str:
    if text:
        lines = text.splitlines(keepends=True)
        text = indent.join(lines)
    return indent + f'""" {text} """' if text else ""


new_literal_structures: Set[str] = set()


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


def format_type(type: _Type, context: FormatTypeContext, preferred_structure_kind: StructureKind) -> str:
    result = "Any"
    if type['kind'] == 'base':
        return format_base_types(type)
    elif type['kind'] == 'reference':
        literal_symbol_name = type['name']
        return f"'{literal_symbol_name}'"
    elif type['kind'] == 'array':
        literal_symbol_name = format_type(type['element'], context, preferred_structure_kind)
        return f"List[{literal_symbol_name}]"
    elif type['kind'] == 'map':
        key = format_base_types(type['key'])
        value = format_type(type['value'], {
            'root_symbol_name': key
        }, preferred_structure_kind)
        return f"Dict[{key}, {value}]"
    elif type['kind'] == 'and':
        pass
    elif type['kind'] == 'or':
        tuple = []
        for item in type['items']:
            tuple.append(format_type(item, context, preferred_structure_kind))
        return f"Union[{', '.join(tuple)}]"
    elif type['kind'] == 'tuple':
        tuple = []
        for item in type['items']:
            tuple.append(format_type(item, context, preferred_structure_kind))
        return f"List[Union[{', '.join(tuple)}]]"
    elif type['kind'] == 'literal':
        if not type['value']['properties']:
            return 'dict'
        root_symbol_name = capitalize(context['root_symbol_name'])
        literal_symbol_name = f"__{root_symbol_name}_Type"
        symbol_id = SymbolNameTracker.get_symbol_id(literal_symbol_name)
        literal_symbol_name += f"_{symbol_id}"
        properties = get_formatted_properties(type['value']['properties'], root_symbol_name, preferred_structure_kind)
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
{indentation}{formatted_properties or 'pass'}
""")
        return f"'{literal_symbol_name}'"
    elif type['kind'] == 'stringLiteral':
        return f"Literal['{type['value']}']"
    elif type['kind'] == "integerLiteral":
        return f"Literal[{type['value']}]"
    elif type['kind'] == "booleanLiteral":
        return f"Literal[{type['value']}]"
    return result


def format_base_types(base_type: Union[BaseType, MapKeyType]):
    if base_type['name'] == 'integer':
        return 'int'
    if base_type['name'] == 'uinteger':
        return 'Uint'
    if base_type['name'] == 'decimal':
        return 'float'
    if base_type['name'] == 'string':
        return 'str'
    if base_type['name'] == 'boolean':
        return 'bool'
    if base_type['name'] == 'null':
        return 'None'

    return f"'{base_type['name']}'"


class FormattedProperty(TypedDict):
    name: str
    value: Any
    documentation: str


def get_formatted_properties(properties: List[Property], root_symbol_name, preferred_structure_kind: StructureKind) -> List[FormattedProperty]:
    result: List[FormattedProperty] = []
    for p in properties:
        key = p['name']
        value = format_type(p['type'], {
            'root_symbol_name': root_symbol_name + "_" + key
        }, preferred_structure_kind)
        if p.get('optional'):
            value = f"NotRequired[{value}]"
        documentation = p.get('documentation') or ""
        result.append({
            'name': key,
            'value': value,
            'documentation': documentation
        })  # f"{key}: {value}{documentation}"

    return result  # "\n\t".join(result)


def has_invalid_property_name(properties: List[Property]):
    for p in properties:
        if keyword.iskeyword(p['name']):
            return True
    return False


def format_class_properties(properties: List[FormattedProperty]) -> str:
    result: List[str] = []
    for p in properties:
        line = f"{p['name']}: {p['value']}"
        comment = format_comment(p['documentation'], indentation)
        if comment:
            line += f"\n{comment}"
        result.append(line)
    return f"\n{indentation}".join(result)


def format_dict_properties(properties: List[FormattedProperty]) -> str:
    result: List[str] = []
    for p in properties:
        documentation = p.get('documentation')
        formatted_documentation = ''
        if documentation:
            formatted_documentation = documentation.replace('\n', f'\n{indentation}# ')
            formatted_documentation = f'# {formatted_documentation}\n{indentation}'
        result.append(f"{formatted_documentation}'{p['name']}': {p['value']},")
    return f"\n{indentation}".join(result)
