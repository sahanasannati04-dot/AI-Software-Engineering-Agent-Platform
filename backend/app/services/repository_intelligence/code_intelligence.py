from pathlib import Path

from app.services.repository_intelligence.code_parser import (
    parse_python_file,
)


def analyze_python_files(
    repository_path: str,
) -> list[dict]:
    root = Path(repository_path)

    if not root.exists():
        raise FileNotFoundError(
            f"Repository path does not exist: {repository_path}"
        )

    if not root.is_dir():
        raise NotADirectoryError(
            f"Repository path is not a directory: {repository_path}"
        )

    python_files = sorted(
        root.rglob("*.py")
    )

    results = []

    for file_path in python_files:
        relative_path = file_path.relative_to(root)

        if any(
            part in {
                ".git",
                ".venv",
                "venv",
                "env",
                "node_modules",
                "__pycache__",
                ".pytest_cache",
                ".mypy_cache",
                ".ruff_cache",
            }
            for part in relative_path.parts
        ):
            continue

        result = parse_python_file(
            str(file_path)
        )

        result["path"] = str(relative_path)

        results.append(result)

    return results