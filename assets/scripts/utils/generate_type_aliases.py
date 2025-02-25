from ..lsp_schema import TypeAlias
from .helpers import StructureKind, format_comment, format_type


def generate_type_aliases(type_aliases: list[TypeAlias]) -> list[str]:
    def toString(type_alias: TypeAlias) -> str:
        symbol_name = type_alias["name"]
        documentation = format_comment(type_alias.get("documentation"))
        if type_alias["name"] == "LSPAny":
            value = "Any"
        else:
            value = format_type(
                type_alias["type"],
                {"root_symbol_name": symbol_name},
                StructureKind.Class,
            )
        result = f"""
{symbol_name} = {value}"""
        if documentation:
            result += f"""\n{documentation}"""
        return result

    return [toString(type_alias) for type_alias in type_aliases]
