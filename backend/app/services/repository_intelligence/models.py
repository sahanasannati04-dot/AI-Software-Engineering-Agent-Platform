from dataclasses import dataclass, field


@dataclass
class FileInfo:
    path: str
    extension: str
    size_bytes: int


@dataclass
class RepositorySnapshot:
    repository_path: str
    file_count: int
    directory_count: int
    files: list[FileInfo] = field(default_factory=list)
    directories: list[str] = field(default_factory=list)