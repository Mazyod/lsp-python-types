from typing import List
from ..lsp_schema import TypeAlias
from .helpers import format_comment, format_type, StructureKind


def generate_type_aliases(type_aliases: List[TypeAlias], preferred_structure_kind: StructureKind) -> List[str]:

    def toString(type_alias: TypeAlias) -> str:
        symbol_name = type_alias['name']
        documentation = format_comment(type_alias.get('documentation'))
        value = format_type(type_alias['type'], {
            'root_symbol_name': symbol_name
        }, preferred_structure_kind)
        result = f"""
{symbol_name} = {value}"""
        if documentation:
            result += f"""\n{documentation}"""
        return result

    return [toString(type_alias) for type_alias in type_aliases]
