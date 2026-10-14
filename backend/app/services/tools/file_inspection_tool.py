from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.code_chunk import CodeChunk


def inspect_file(
    db: Session,
    repository_id: int,
    path: str,
) -> dict:
    """
    Inspect all indexed code chunks belonging to a specific file.
    """

    if not path.strip():
        return {
            "repository_id": repository_id,
            "path": path,
            "exists": False,
            "chunks": [],
            "chunk_count": 0,
        }

    chunks = list(
        db.scalars(
            select(CodeChunk)
            .where(
                CodeChunk.repository_id == repository_id,
                CodeChunk.path == path,
            )
            .order_by(CodeChunk.start_line)
        )
    )

    return {
        "repository_id": repository_id,
        "path": path,
        "exists": bool(chunks),
        "chunks": [
            {
                "chunk_id": chunk.id,
                "chunk_type": chunk.chunk_type,
                "symbol_name": chunk.symbol_name,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "content": chunk.content,
            }
            for chunk in chunks
        ],
        "chunk_count": len(chunks),
    }