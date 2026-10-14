from pathlib import Path


IGNORED_DIRECTORIES = {
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


def build_repository_tree(
    repository_path: str,
) -> dict:
    root = Path(repository_path)

    if not root.exists():
        raise FileNotFoundError(
            f"Repository path does not exist: {repository_path}"
        )

    if not root.is_dir():
        raise NotADirectoryError(
            f"Repository path is not a directory: {repository_path}"
        )

    def build_node(
        directory: Path,
    ) -> dict:
        children = []

        entries = sorted(
            directory.iterdir(),
            key=lambda path: (
                not path.is_dir(),
                path.name.lower(),
            ),
        )

        for path in entries:
            if path.name in IGNORED_DIRECTORIES:
                continue

            if path.is_dir():
                children.append(
                    {
                        "name": path.name,
                        "type": "directory",
                        "children": build_node(path)[
                            "children"
                        ],
                    }
                )

            elif path.is_file():
                children.append(
                    {
                        "name": path.name,
                        "type": "file",
                    }
                )

        return {
            "name": directory.name,
            "type": "directory",
            "children": children,
        }

    return build_node(root)