from collections import Counter

from app.services.repository_intelligence.models import (
    RepositorySnapshot,
)


EXTENSION_TO_LANGUAGE = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".c": "C",
    ".cs": "C#",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "Sass",
    ".vue": "Vue",
    ".sql": "SQL",
    ".sh": "Shell",
    ".ps1": "PowerShell",
}


def detect_languages(
    snapshot: RepositorySnapshot,
) -> dict[str, int]:
    language_counts = Counter()

    for file_info in snapshot.files:
        language = EXTENSION_TO_LANGUAGE.get(
            file_info.extension
        )

        if language:
            language_counts[language] += 1

    return dict(
        language_counts.most_common()
    )