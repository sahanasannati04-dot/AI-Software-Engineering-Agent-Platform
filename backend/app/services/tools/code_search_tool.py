from sqlalchemy.orm import Session

from app.services.repository_intelligence.vector_retrieval import (
    retrieve_similar_chunks,
)


def search_code(
    db: Session,
    repository_id: int,
    query: str,
    limit: int = 5,
) -> list[dict]:
    """
    Search the repository for code relevant to the user's query.
    """

    if not query.strip():
        return []

    chunks = retrieve_similar_chunks(
        db=db,
        repository_id=repository_id,
        query=query,
        limit=limit,
    )

    results = []

    for chunk in chunks:
        results.append(
            {
                "path": chunk.path,
                "symbol_name": chunk.symbol_name,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "chunk_type": chunk.chunk_type,
                "content": chunk.content,
                "relevance_score": chunk.relevance_score,
            }
        )

    return results