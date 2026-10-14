from app.services.repository_intelligence.code_intelligence import (
    analyze_python_files,
)
from app.services.repository_intelligence.code_search import (
    search_repository,
)
from app.services.repository_intelligence.dependency_detector import (
    detect_dependencies,
)
from app.services.repository_intelligence.file_classifier import (
    classify_repository,
)
from app.services.repository_intelligence.language_detector import (
    detect_languages,
)
from app.services.repository_intelligence.repository_metadata import (
    detect_repository_metadata,
)
from app.services.repository_intelligence.report import (
    build_repository_report,
)
from app.services.repository_intelligence.scanner import (
    scan_repository,
)
from app.services.repository_intelligence.structure_mapper import (
    build_repository_tree,
)
from app.services.repository_intelligence.symbol_index import (
    build_symbol_index,
)


def analyze_repository(
    repository_path: str,
) -> dict:
    snapshot = scan_repository(repository_path)

    languages = detect_languages(snapshot)

    file_classification = classify_repository(snapshot)

    dependencies = detect_dependencies(repository_path)

    metadata = detect_repository_metadata(repository_path)

    code_intelligence = analyze_python_files(
        repository_path
    )

    structure = build_repository_tree(
        repository_path
    )

    symbol_index = build_symbol_index(
        code_intelligence
    )

    analysis = {
        "repository": {
            "path": snapshot.repository_path,
            "file_count": snapshot.file_count,
            "directory_count": snapshot.directory_count,
        },
        "languages": languages,
        "file_classification": file_classification,
        "dependencies": dependencies,
        "metadata": metadata,
        "code_intelligence": code_intelligence,
        "structure": structure,
        "symbol_index": symbol_index,
    }

    analysis["report"] = build_repository_report(
        analysis
    )

    return analysis


def search_repository_code(
    repository_path: str,
    query: str,
    max_results: int = 10,
) -> list[dict]:
    code_intelligence = analyze_python_files(
        repository_path
    )

    return search_repository(
        repository_path=repository_path,
        query=query,
        max_results=max_results,
        code_intelligence=code_intelligence,
    )