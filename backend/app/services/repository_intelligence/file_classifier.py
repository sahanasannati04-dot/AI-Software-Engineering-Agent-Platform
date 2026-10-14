from app.services.repository_intelligence.models import (
    FileInfo,
    RepositorySnapshot,
)


CONFIGURATION_FILES = {
    ".env",
    ".env.example",
    ".gitignore",
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "alembic.ini",
    "pyproject.toml",
    "requirements.txt",
    "package.json",
    "tsconfig.json",
}


DOCUMENTATION_FILES = {
    "readme",
    "readme.md",
    "readme.txt",
    "changelog.md",
    "license",
}


TEST_DIRECTORIES = {
    "test",
    "tests",
    "__tests__",
}


DATA_EXTENSIONS = {
    ".json",
    ".csv",
    ".xml",
    ".yaml",
    ".yml",
    ".toml",
}


SOURCE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".cpp",
    ".cc",
    ".cxx",
    ".c",
    ".cs",
    ".php",
    ".rb",
    ".swift",
    ".kt",
    ".kts",
    ".vue",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".sass",
}


def classify_file(file_info: FileInfo) -> str:
    path = file_info.path.replace("\\", "/")
    filename = path.rsplit("/", maxsplit=1)[-1]
    filename_lower = filename.lower()

    path_parts = {
        part.lower()
        for part in path.split("/")
    }

    if filename_lower in CONFIGURATION_FILES:
        return "configuration"

    if filename_lower in DOCUMENTATION_FILES:
        return "documentation"

    if TEST_DIRECTORIES.intersection(path_parts):
        return "test"

    if file_info.extension in DATA_EXTENSIONS:
        return "data"

    if file_info.extension in SOURCE_EXTENSIONS:
        return "source_code"

    return "other"


def classify_repository(
    snapshot: RepositorySnapshot,
) -> dict[str, int]:
    classifications: dict[str, int] = {
        "source_code": 0,
        "test": 0,
        "configuration": 0,
        "documentation": 0,
        "data": 0,
        "other": 0,
    }

    for file_info in snapshot.files:
        category = classify_file(file_info)
        classifications[category] += 1

    return classifications