from dataclasses import dataclass


@dataclass
class CodeChunk:
    chunk_id: str
    path: str
    content: str
    chunk_type: str
    symbol_name: str | None = None
    start_line: int | None = None
    end_line: int | None = None

import ast
from pathlib import Path

def chunk_python_file(
    file_path: str,
    repository_path: str,
) -> list[CodeChunk]:
    root = Path(repository_path)
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Python file does not exist: {file_path}"
        )

    source = path.read_text(
        encoding="utf-8"
    )

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    lines = source.splitlines()
    chunks = []

    relative_path = path.relative_to(root)

    for node in ast.walk(tree):
        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):
            continue

        if not hasattr(node, "lineno"):
            continue

        start_line = node.lineno
        end_line = getattr(
            node,
            "end_lineno",
            start_line,
        )

        content = "\n".join(
            lines[start_line - 1:end_line]
        )

        chunk_type = (
            "class"
            if isinstance(node, ast.ClassDef)
            else "function"
        )

        chunk_id = (
            f"{relative_path}:"
            f"{start_line}:"
            f"{end_line}"
        )

        chunks.append(
            CodeChunk(
                chunk_id=chunk_id,
                path=str(relative_path),
                content=content,
                chunk_type=chunk_type,
                symbol_name=node.name,
                start_line=start_line,
                end_line=end_line,
            )
        )

    return sorted(
        chunks,
        key=lambda chunk: (
            chunk.start_line or 0
        ),
    )

def chunk_repository(
    repository_path: str,
) -> list[CodeChunk]:
    root = Path(repository_path)

    if not root.exists():
        raise FileNotFoundError(
            f"Repository path does not exist: {repository_path}"
        )

    if not root.is_dir():
        raise NotADirectoryError(
            f"Repository path is not a directory: {repository_path}"
        )

    ignored_directories = {
        ".git",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".next",
        "dist",
        "build",
    }

    all_chunks = []

    for file_path in sorted(
        root.rglob("*.py")
    ):
        relative_path = file_path.relative_to(root)

        if any(
            part in ignored_directories
            for part in relative_path.parts
        ):
            continue

        file_chunks = chunk_python_file(
            str(file_path),
            repository_path,
        )

        all_chunks.extend(file_chunks)

    return all_chunks

def summarize_chunks(
    chunks: list[CodeChunk],
) -> dict[str, int]:
    summary = {
        "total": len(chunks),
        "classes": 0,
        "functions": 0,
    }

    for chunk in chunks:
        if chunk.chunk_type == "class":
            summary["classes"] += 1

        elif chunk.chunk_type == "function":
            summary["functions"] += 1

    return summary
