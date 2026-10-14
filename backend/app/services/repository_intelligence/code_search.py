from pathlib import Path


def search_repository(
    repository_path: str,
    query: str,
    max_results: int = 10,
    code_intelligence: list[dict] | None = None,
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

    query = query.strip().lower()

    if not query:
        return []

    results = []

    if code_intelligence:
        for file_info in code_intelligence:
            file_path = file_info["path"]

            for class_name in file_info.get(
                "classes",
                [],
            ):
                if query in class_name.lower():
                    results.append(
                        {
                            "type": "class",
                            "name": class_name,
                            "path": file_path,
                        }
                    )

            for function_name in file_info.get(
                "functions",
                [],
            ):
                if query in function_name.lower():
                    results.append(
                        {
                            "type": "function",
                            "name": function_name,
                            "path": file_path,
                        }
                    )

            if len(results) >= max_results:
                return results[:max_results]

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

    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue

        relative_path = file_path.relative_to(root)

        if any(
            part in ignored_directories
            for part in relative_path.parts
        ):
            continue

        try:
            content = file_path.read_text(
                encoding="utf-8"
            )
        except (
            UnicodeDecodeError,
            OSError,
        ):
            continue

        lines = content.splitlines()

        for line_number, line in enumerate(
            lines,
            start=1,
        ):
            if query not in line.lower():
                continue

            results.append(
                {
                    "type": "text",
                    "path": str(relative_path),
                    "line_number": line_number,
                    "line": line.strip(),
                }
            )

            if len(results) >= max_results:
                return results

    return results