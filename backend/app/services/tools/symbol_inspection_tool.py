from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.code_chunk import CodeChunk


def inspect_symbol(
    db: Session,
    repository_id: int,
    symbol_name: str,
) -> dict:
    """
    Inspect indexed code chunks matching a specific symbol name.
    """

    if not symbol_name.strip():
        return {
            "repository_id": repository_id,
            "symbol_name": symbol_name,
            "exists": False,
            "matches": [],
            "match_count": 0,
        }

    chunks = list(
        db.scalars(
            select(CodeChunk)
            .where(
                CodeChunk.repository_id == repository_id,
                CodeChunk.symbol_name == symbol_name,
            )
            .order_by(CodeChunk.path, CodeChunk.start_line)
        )
    )

    return {
        "repository_id": repository_id,
        "symbol_name": symbol_name,
        "exists": bool(chunks),
        "matches": [
            {
                "path": chunk.path,
                "chunk_type": chunk.chunk_type,
                "symbol_name": chunk.symbol_name,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "content": chunk.content,
            }
            for chunk in chunks
        ],
        "match_count": len(chunks),
    }