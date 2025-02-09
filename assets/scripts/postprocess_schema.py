#!/usr/bin/env python3

from pathlib import Path


def fix_kind_fields(content: str) -> str:
    # Map of class names to their kind literal values from the schema
    kind_map = {
        "AndType": "and",
        "ArrayType": "array",
        "BaseType": "base",
        "BooleanLiteralType": "booleanLiteral",
        "EnumerationType": "base",
        "IntegerLiteralType": "integerLiteral",
        "MapKeyType1": "base",
        "MapType": "map",
        "OrType": "or",
        "ReferenceType": "reference",
        "StringLiteralType": "stringLiteral",
        "StructureLiteralType": "literal",
        "TupleType": "tuple",
    }

    # For each class that needs fixing
    for class_name, kind_value in kind_map.items():
        # Find the class definition
        class_start = content.find(f"class {class_name}(TypedDict):")
        if class_start == -1:
            continue

        # Find the next class definition or end of file
        next_class = content.find("class ", class_start + 1)
        class_end = next_class if next_class != -1 else len(content)
        class_content = content[class_start:class_end]

        # Find the kind field, handling possible docstring
        kind_lines = [
            line
            for line in class_content.split("\n")
            if "kind:" in line and "NotRequired[str]" in line
        ]

        if not kind_lines:
            continue

        kind_line = kind_lines[0]
        indent = " " * (len(kind_line) - len(kind_line.lstrip()))

        # Create the replacement line
        new_kind_line = f'{indent}kind: Literal["{kind_value}"]'

        # Handle docstring if present
        if '"""' in kind_line:
            docstring = kind_line[kind_line.find('"""') :]
            new_kind_line = f"{new_kind_line} {docstring}"

        # Replace the old line with the new one
        modified_content = class_content.replace(kind_line, new_kind_line)
        content = content[:class_start] + modified_content + content[class_end:]

    return content


def main():
    # Get the script directory
    script_dir = Path(__file__).parent

    # Read the generated schema
    schema_path = script_dir / "lsp_schema.py"
    content = schema_path.read_text()

    # Fix the kind fields
    modified_content = fix_kind_fields(content)

    # Write back the modified content
    schema_path.write_text(modified_content)


if __name__ == "__main__":
    main()
