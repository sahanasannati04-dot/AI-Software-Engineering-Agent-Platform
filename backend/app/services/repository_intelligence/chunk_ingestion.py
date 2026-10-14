from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.code_chunk import CodeChunk
from app.services.repository_intelligence.chunker import chunk_repository
from app.services.repository_intelligence.embeddings import (
    EmbeddingProvider,
    GeminiEmbeddingProvider,
)


def ingest_repository_chunks(
    db: Session,
    repository_id: int,
    repository_path: str,
    embedding_provider: EmbeddingProvider | None = None,
) -> dict[str, int]:
    provider = (
        embedding_provider
        or GeminiEmbeddingProvider(
            model="gemini-embedding-2",
            dimensions=128,
        )
    )

    chunks = chunk_repository(repository_path)

    db.execute(
        delete(CodeChunk).where(
            CodeChunk.repository_id == repository_id
        )
    )

    if not chunks:
        db.commit()

        return {
            "repository_id": repository_id,
            "chunks_created": 0,
        }

    embeddings = provider.embed_texts(
        [chunk.content for chunk in chunks]
    )

    database_chunks = []

    for chunk, embedding in zip(chunks, embeddings):
        database_chunk = CodeChunk(
            repository_id=repository_id,
            chunk_id=chunk.chunk_id,
            path=chunk.path,
            content=chunk.content,
            chunk_type=chunk.chunk_type,
            symbol_name=chunk.symbol_name,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            embedding=embedding,
        )

        database_chunks.append(database_chunk)

    db.add_all(database_chunks)
    db.commit()

    return {
        "repository_id": repository_id,
        "chunks_created": len(database_chunks),
    }