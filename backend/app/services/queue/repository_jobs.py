from app.db.session import SessionLocal
from app.models.repository import Repository
from app.services.repository.repository_service import RepositoryService
from app.services.repository.workspace_service import RepositoryWorkspaceService
from app.services.repository_intelligence.chunk_ingestion import (
    ingest_repository_chunks,
)


repository_service = RepositoryService()
workspace_service = RepositoryWorkspaceService()


async def ingest_repository_job(
    ctx,
    repository_id: int,
) -> dict:
    db = SessionLocal()

    try:
        repository = db.get(
            Repository,
            repository_id,
        )

        if not repository:
            raise ValueError(
                f"Repository {repository_id} not found."
            )

        repository_service.mark_cloning(repository)
        db.commit()

        workspace_id, repository_path = (
            workspace_service.clone_repository(
                repository_url=repository.url,
                branch=repository.default_branch,
            )
        )

        repository.workspace_id = workspace_id
        repository_service.mark_connected(repository)
        db.commit()

        repository_service.mark_analyzing(repository)
        db.commit()

        ingestion_result = ingest_repository_chunks(
            db=db,
            repository_id=repository.id,
            repository_path=str(repository_path),
        )

        repository_service.mark_ready(repository)
        db.commit()

        return {
            "repository_id": repository.id,
            "workspace_id": workspace_id,
            "status": repository.status,
            "chunks_created": ingestion_result[
                "chunks_created"
            ],
        }

    except Exception:
        db.rollback()

        repository = db.get(
            Repository,
            repository_id,
        )

        if repository:
            try:
                repository_service.mark_failed(repository)
                db.commit()
            except Exception:
                db.rollback()

        raise

    finally:
        db.close()