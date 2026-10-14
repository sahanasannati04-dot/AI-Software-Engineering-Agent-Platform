from pathlib import Path

from app.services.repository_intelligence.models import (
    FileInfo,
    RepositorySnapshot,
)


IGNORED_DIRECTORIES = {
    ".git",
    ".github",
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


def scan_repository(repository_path: str) -> RepositorySnapshot:
    root = Path(repository_path)

    if not root.exists():
        raise FileNotFoundError(
            f"Repository path does not exist: {repository_path}"
        )

    if not root.is_dir():
        raise NotADirectoryError(
            f"Repository path is not a directory: {repository_path}"
        )

    files = []
    directories = []

    for path in root.rglob("*"):
        relative_path = path.relative_to(root)

        if any(
            part in IGNORED_DIRECTORIES
            for part in relative_path.parts
        ):
            continue

        if path.is_dir():
            directories.append(str(relative_path))

        elif path.is_file():
            files.append(
                FileInfo(
                    path=str(relative_path),
                    extension=path.suffix.lower(),
                    size_bytes=path.stat().st_size,
                )
            )

    return RepositorySnapshot(
        repository_path=str(root),
        file_count=len(files),
        directory_count=len(directories),
        files=files,
        directories=directories,
    )