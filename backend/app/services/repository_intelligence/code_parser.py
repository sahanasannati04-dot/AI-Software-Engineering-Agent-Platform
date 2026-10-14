import ast
from pathlib import Path


def parse_python_file(
    file_path: str,
) -> dict:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Python file does not exist: {file_path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Path is not a file: {file_path}"
        )

    source = path.read_text(
        encoding="utf-8"
    )

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return {
            "path": str(path),
            "error": "SyntaxError",
            "message": str(exc),
            "imports": [],
            "classes": [],
            "functions": [],
        }

    imports = []
    classes = []
    functions = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)

        elif isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            functions.append(node.name)

    return {
        "path": str(path),
        "error": None,
        "imports": sorted(set(imports)),
        "classes": sorted(set(classes)),
        "functions": sorted(set(functions)),
    }