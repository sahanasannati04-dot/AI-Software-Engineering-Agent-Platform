from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.project import Project
from app.models.repository import Repository
from app.models.user import User
from app.schemas.repository_question import (
    RepositoryQuestionRequest,
    RepositoryQuestionResponse,
    RepositorySource,
)
from app.services.repository_intelligence.rag_service import (
    answer_repository_question,
)


router = APIRouter(
    prefix="/repository-questions",
    tags=["Repository Questions"],
)


@router.post(
    "/{project_id}/{repository_id}",
    response_model=RepositoryQuestionResponse,
)
def ask_repository_question(
    project_id: int,
    repository_id: int,
    question_data: RepositoryQuestionRequest,
    conversation_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repository = db.scalar(
        select(Repository)
        .join(Project)
        .where(
            Repository.id == repository_id,
            Repository.project_id == project_id,
            Project.owner_id == current_user.id,
        )
    )

    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found.",
        )

    if not question_data.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty.",
        )

    try:
        result = answer_repository_question(
            db=db,
            repository_id=repository.id,
            question=question_data.question,
            conversation_id=conversation_id,
            user_id=current_user.id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The repository AI service is temporarily "
                "unavailable. Please try again later."
            ),
        ) from exc

    sources = [
        RepositorySource(**source)
        for source in result["sources"]
    ]

    return RepositoryQuestionResponse(
        repository_id=repository.id,
        question=question_data.question,
        answer=result["answer"],
        intent=result["intent"],
        intent_confidence=result["intent_confidence"],
        sources=sources,
    )