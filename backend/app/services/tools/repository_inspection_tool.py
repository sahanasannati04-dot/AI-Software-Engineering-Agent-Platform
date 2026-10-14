from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.repository import Repository
from app.models.code_chunk import CodeChunk


def inspect_repository(
    db: Session,
    repository_id: int,
) -> dict:
    """
    Inspect basic repository information and indexed code structure.
    """

    repository = db.scalar(
        select(Repository).where(
            Repository.id == repository_id
        )
    )

    if not repository:
        return {
            "repository_id": repository_id,
            "exists": False,
            "files": [],
            "file_count": 0,
        }

    chunks = list(
        db.scalars(
            select(CodeChunk).where(
                CodeChunk.repository_id == repository_id
            )
        )
    )

    files = sorted(
        {
            chunk.path
            for chunk in chunks
            if chunk.path
        }
    )

    return {
        "repository_id": repository.id,
        "exists": True,
        "repository_name": repository.name,
        "repository_url": getattr(
            repository,
            "url",
            None,
        ),
        "files": files,
        "file_count": len(files),
    }