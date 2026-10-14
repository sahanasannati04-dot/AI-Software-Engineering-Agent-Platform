from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.project import Project
from app.models.repository import Repository
from app.models.user import User
from app.schemas.repository import (
    RepositoryCreate,
    RepositoryResponse,
)
from app.services.queue.client import (
    enqueue_repository_ingestion,
)
from app.services.repository.repository_service import (
    RepositoryService,
)
from app.services.repository.workspace_service import (
    RepositoryWorkspaceService,
)


router = APIRouter(
    prefix="/repositories",
    tags=["Repositories"],
)

workspace_service = RepositoryWorkspaceService()
repository_service = RepositoryService()


@router.post(
    "/{project_id}",
    response_model=RepositoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_repository(
    project_id: int,
    repository_data: RepositoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    repository_url = str(repository_data.url).rstrip("/")

    repository = Repository(
        name=repository_data.name,
        url=repository_url,
        default_branch=repository_data.default_branch,
        language=repository_data.language,
        project_id=project.id,
        status="pending",
    )

    db.add(repository)
    db.commit()
    db.refresh(repository)

    try:
        await enqueue_repository_ingestion(
            repository_id=repository.id,
        )

    except Exception as exc:
        failed_repository = db.get(
            Repository,
            repository.id,
        )

        if failed_repository:
            try:
                repository_service.mark_failed(
                    failed_repository
                )
                db.commit()
                db.refresh(failed_repository)
            except Exception:
                db.rollback()

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Repository was created, but the ingestion "
                f"job could not be queued: {exc}"
            ),
        ) from exc

    return repository


@router.get(
    "/{repository_id}",
    response_model=RepositoryResponse,
)
def get_repository(
    repository_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repository = db.scalar(
        select(Repository)
        .join(Project)
        .where(
            Repository.id == repository_id,
            Project.owner_id == current_user.id,
        )
    )

    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found.",
        )

    return repository


@router.get(
    "/project/{project_id}",
    response_model=list[RepositoryResponse],
)
def get_project_repositories(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    repositories = list(
        db.scalars(
            select(Repository)
            .where(
                Repository.project_id == project_id,
            )
            .order_by(Repository.id)
        )
    )

    return repositories


@router.get(
    "/{repository_id}/verify",
)
def verify_repository_workspace(
    repository_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repository = db.scalar(
        select(Repository)
        .join(Project)
        .where(
            Repository.id == repository_id,
            Project.owner_id == current_user.id,
        )
    )

    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found.",
        )

    if not repository.workspace_id:
        return {
            "repository_id": repository.id,
            "workspace_id": None,
            "exists": False,
            "valid_git_repository": False,
        }

    exists = workspace_service.workspace_exists(
        repository.workspace_id
    )

    valid_git_repository = (
        workspace_service.verify_workspace(
            repository.workspace_id
        )
        if exists
        else False
    )

    return {
        "repository_id": repository.id,
        "workspace_id": repository.workspace_id,
        "exists": exists,
        "valid_git_repository": valid_git_repository,
    }


@router.delete(
    "/{repository_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_repository(
    repository_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repository = db.scalar(
        select(Repository)
        .join(Project)
        .where(
            Repository.id == repository_id,
            Project.owner_id == current_user.id,
        )
    )

    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found.",
        )

    workspace_id = repository.workspace_id

    db.delete(repository)
    db.commit()

    if workspace_id:
        workspace_service.delete_workspace(
            workspace_id
        )

    return None