from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.code_chunk import CodeChunk
from app.services.repository_intelligence.embeddings import (
    EmbeddingProvider,
    LocalEmbeddingProvider,
)


@dataclass
class VectorSearchResult:
    chunk_id: str
    path: str
    content: str
    chunk_type: str
    symbol_name: str | None
    start_line: int | None
    end_line: int | None
    distance: float


def search_similar_code(
    db: Session,
    repository_id: int,
    query: str,
    limit: int = 5,
    embedding_provider: EmbeddingProvider | None = None,
) -> list[VectorSearchResult]:
    """
    Search repository code chunks using pgvector cosine distance.
    """

    if not query.strip():
        return []

    if limit < 1:
        return []

    provider = embedding_provider or LocalEmbeddingProvider(
        dimensions=128
    )

    query_embedding = provider.embed_text(query)

    distance_expression = (
        CodeChunk.embedding.cosine_distance(
            query_embedding
        )
    )

    statement = (
        select(
            CodeChunk,
            distance_expression.label("distance"),
        )
        .where(
            CodeChunk.repository_id == repository_id,
            CodeChunk.embedding.is_not(None),
        )
        .order_by(distance_expression)
        .limit(limit)
    )

    rows = db.execute(statement).all()

    return [
        VectorSearchResult(
            chunk_id=chunk.chunk_id,
            path=chunk.path,
            content=chunk.content,
            chunk_type=chunk.chunk_type,
            symbol_name=chunk.symbol_name,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            distance=float(distance),
        )
        for chunk, distance in rows
    ]