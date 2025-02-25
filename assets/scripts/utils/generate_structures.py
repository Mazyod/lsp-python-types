from ..lsp_schema import Structure
from .helpers import (FormattedProperty, StructureKind,
                      format_class_properties, format_comment,
                      format_dict_properties, get_formatted_properties,
                      has_invalid_property_name, indentation)


def generate_structures(structures: list[Structure]) -> list[str]:

    def toString(structure: Structure) -> str:
        kind = StructureKind.Class
        if has_invalid_property_name(structure['properties']):
            kind = StructureKind.Function
        return generate_structure(structure, structures, kind)

    return [toString(structure) for structure in structures if not structure['name'].startswith('_')]


def get_additional_properties(for_structure: Structure, structures: list[Structure], structure_kind: StructureKind) -> list[FormattedProperty]:
    """Returns properties from extended and mixin types. """
    result: list[FormattedProperty] = []
    additional_structures = for_structure.get('extends') or []
    additional_structures.extend(for_structure.get('mixins') or [])
    for additional_structure in additional_structures:
        if additional_structure['kind'] != 'reference':
            raise Exception("Cannot generate extends. Currently only supports kind: 'reference', but received:", additional_structure['kind'])
        structure = next(structure for structure in structures if structure["name"] == additional_structure['name'])
        if structure:
            properties = get_formatted_properties(structure['properties'], structure['name'], structure_kind)
            result.extend(properties)
    return result


def generate_structure(structure: Structure, structures: list[Structure], structure_kind: StructureKind) -> str:
    result = ""
    symbol_name = structure['name']
    properties = get_formatted_properties(structure['properties'], structure['name'], structure_kind)
    additional_properties = get_additional_properties(structure, structures, structure_kind)

    # add extended properties
    taken_property_names = [property['name'] for property in properties]
    for additional_property in additional_properties:
        if additional_property['name'] not in taken_property_names:
            properties.append(additional_property)

    if structure_kind == StructureKind.Function:
        documentation = format_comment(structure.get('documentation'), '')
        result += f"{symbol_name} = TypedDict('{symbol_name}', "
        result += "{\n"
        result += f"{indentation}{format_dict_properties(properties)}\n"
        result += "})"
        if documentation:
            result += f'\n{documentation}'
    else:
        documentation = format_comment(structure.get('documentation'), indentation)
        result += f"class {symbol_name}(TypedDict):\n"
        if documentation:
            result += f"{documentation}\n"
        result += f"{indentation}{format_class_properties(properties) or 'pass'}"
    return result
