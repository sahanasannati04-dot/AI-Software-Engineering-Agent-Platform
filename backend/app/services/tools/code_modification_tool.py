from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.code_modification import CodeModification
from app.models.project import Project
from app.models.repository import Repository
from app.services.repository.workspace_service import (
    RepositoryWorkspaceService,
)
from app.services.tools.code_search_tool import search_code
from app.services.tools.code_modification_service import (
    AppliedModification,
    CodeModificationService,
    ProposedModification,
)


workspace_service = RepositoryWorkspaceService()
modification_service = CodeModificationService()


def _get_repository_workspace_path(
    db: Session,
    repository_id: int,
) -> str:
    """
    Resolve the local workspace path for a repository.
    """

    repository = db.scalar(
        select(Repository)
        .join(Project)
        .where(
            Repository.id == repository_id,
        )
    )

    if not repository:
        raise ValueError("Repository not found.")

    if not repository.workspace_id:
        raise ValueError(
            "Repository does not have a connected workspace."
        )

    workspace_path = workspace_service.get_workspace_path(
        repository.workspace_id
    )

    if not workspace_path.exists():
        raise ValueError(
            "Repository workspace does not exist."
        )

    return str(workspace_path)


def _build_context(
    matches: list[dict],
) -> str:
    """
    Build readable repository context from search matches.
    """

    sections = []

    for index, match in enumerate(
        matches,
        start=1,
    ):
        location = match["path"]

        if match["start_line"] is not None:
            location += f":{match['start_line']}"

            if match["end_line"] is not None:
                location += f"-{match['end_line']}"

        sections.append(
            f"### Relevant Code {index}\n"
            f"File: {location}\n"
            f"Symbol: {match['symbol_name']}\n"
            f"Relevance: {match['relevance_score']:.4f}\n\n"
            f"{match['content']}"
        )

    return "\n\n".join(sections)


def _build_proposal(
    repository_path: str,
    file_path: str,
    proposed_content: str,
) -> ProposedModification:
    """
    Create a safe modification proposal.
    """

    return modification_service.prepare_modification(
        repository_path=repository_path,
        file_path=file_path,
        proposed_content=proposed_content,
    )


def _serialize_proposal(
    proposal: ProposedModification,
) -> dict:
    """
    Convert a proposal into a JSON-serializable structure.
    """

    return {
        "repository_path": proposal.repository_path,
        "file_path": proposal.file_path,
        "original_content": proposal.original_content,
        "proposed_content": proposal.proposed_content,
        "diff": proposal.diff,
    }


def _serialize_applied_modification(
    modification: AppliedModification,
) -> dict:
    """
    Convert an applied modification into a JSON-serializable structure.
    """

    return {
        "repository_path": modification.repository_path,
        "file_path": modification.file_path,
        "original_content": modification.original_content,
        "applied_content": modification.applied_content,
        "diff": modification.diff,
    }


def _persist_prepared_modification(
    db: Session | None,
    repository_id: int,
    proposal: ProposedModification,
) -> CodeModification | None:
    """
    Persist a prepared modification when a database session exists.

    When db is None, the existing filesystem-only behavior is preserved.
    """

    if db is None:
        return None

    modification = CodeModification(
        repository_id=repository_id,
        file_path=proposal.file_path,
        status="prepared",
        original_content=proposal.original_content,
        proposed_content=proposal.proposed_content,
        applied_content=None,
        diff=proposal.diff,
        approval_required=True,
    )

    db.add(modification)
    db.commit()
    db.refresh(modification)

    return modification


def _get_persisted_modification(
    db: Session,
    repository_id: int,
    modification_id: int,
) -> CodeModification:
    """
    Retrieve a persisted modification belonging to the requested
    repository.

    The repository ID is always part of the lookup so a modification
    from another repository cannot be used.
    """

    modification = db.scalar(
        select(CodeModification).where(
            CodeModification.id == modification_id,
            CodeModification.repository_id == repository_id,
        )
    )

    if not modification:
        raise ValueError(
            "Code modification record not found."
        )

    return modification


def _validate_persisted_apply(
    db: Session | None,
    repository_id: int,
    modification_id: int | None,
    original_content: str,
    proposed_content: str,
) -> CodeModification | None:
    """
    Validate a persisted modification BEFORE touching the filesystem.

    This is intentionally performed before apply_modification().
    """

    if db is None or modification_id is None:
        return None

    modification = _get_persisted_modification(
        db=db,
        repository_id=repository_id,
        modification_id=modification_id,
    )

    if modification.status != "prepared":
        raise ValueError(
            "Only a prepared modification can be applied."
        )

    if modification.original_content != original_content:
        raise ValueError(
            "Stored original content does not match "
            "the approved modification."
        )

    if modification.proposed_content != proposed_content:
        raise ValueError(
            "Stored proposed content does not match "
            "the approved modification."
        )

    return modification


def _validate_persisted_rollback(
    db: Session | None,
    repository_id: int,
    modification_id: int | None,
) -> CodeModification | None:
    """
    Validate a persisted rollback BEFORE touching the filesystem.
    """

    if db is None or modification_id is None:
        return None

    modification = _get_persisted_modification(
        db=db,
        repository_id=repository_id,
        modification_id=modification_id,
    )

    if modification.status != "applied":
        raise ValueError(
            "Only an applied modification can be rolled back."
        )

    return modification


def _persist_applied_modification(
    db: Session | None,
    modification_id: int | None,
    repository_id: int,
    applied: AppliedModification,
) -> CodeModification | None:
    """
    Persist an applied modification when a database session exists.

    Validation for an existing modification must already have happened
    before the filesystem was changed.
    """

    if db is None:
        return None

    if modification_id is not None:
        modification = _get_persisted_modification(
            db=db,
            repository_id=repository_id,
            modification_id=modification_id,
        )

        if modification.status != "prepared":
            raise ValueError(
                "Only a prepared modification can be applied."
            )

        if (
            modification.original_content
            != applied.original_content
        ):
            raise ValueError(
                "Stored original content does not match "
                "the approved modification."
            )

        if (
            modification.proposed_content
            != applied.applied_content
        ):
            raise ValueError(
                "Stored proposed content does not match "
                "the applied modification."
            )

        modification.applied_content = (
            applied.applied_content
        )
        modification.status = "applied"
        modification.approved_at = datetime.now(timezone.utc)
        modification.applied_at = datetime.now(timezone.utc)
        modification.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(modification)

        return modification

    modification = CodeModification(
        repository_id=repository_id,
        file_path=applied.file_path,
        status="applied",
        original_content=applied.original_content,
        proposed_content=applied.applied_content,
        applied_content=applied.applied_content,
        diff=applied.diff,
        approval_required=False,
        approved_at=datetime.now(timezone.utc),
        applied_at=datetime.now(timezone.utc),
    )

    db.add(modification)
    db.commit()
    db.refresh(modification)

    return modification


def _persist_rollback(
    db: Session | None,
    modification_id: int | None,
    repository_id: int,
) -> CodeModification | None:
    """
    Mark a persisted modification as rolled back.

    The modification must already have been validated before the
    filesystem rollback.
    """

    if db is None or modification_id is None:
        return None

    modification = _get_persisted_modification(
        db=db,
        repository_id=repository_id,
        modification_id=modification_id,
    )

    if modification.status != "applied":
        raise ValueError(
            "Only an applied modification can be rolled back."
        )

    modification.status = "rolled_back"
    modification.rolled_back_at = datetime.now(timezone.utc)
    modification.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(modification)

    return modification


def _prepare_operation(
    db: Session,
    repository_id: int,
    file_path: str,
    proposed_content: str,
) -> dict:
    """
    Prepare a modification without changing repository files.

    When a database session exists, persist the prepared modification.
    """

    repository_path = _get_repository_workspace_path(
        db=db,
        repository_id=repository_id,
    )

    proposal = _build_proposal(
        repository_path=repository_path,
        file_path=file_path,
        proposed_content=proposed_content,
    )

    modification = _persist_prepared_modification(
        db=db,
        repository_id=repository_id,
        proposal=proposal,
    )

    result = {
        "operation": "prepare",
        "repository_id": repository_id,
        "proposal": _serialize_proposal(proposal),
    }

    if modification is not None:
        result.update(
            {
                "modification_id": modification.id,
                "status": modification.status,
                "approval_required": modification.approval_required,
            }
        )

    return result


def _apply_operation(
    db: Session,
    repository_id: int,
    file_path: str,
    original_content: str,
    proposed_content: str,
    diff: str = "",
    modification_id: int | None = None,
) -> dict:
    """
    Apply an explicitly approved modification.

    When a persisted modification ID is supplied, the database record
    is validated BEFORE the filesystem is changed.
    """

    repository_path = _get_repository_workspace_path(
        db=db,
        repository_id=repository_id,
    )

    _validate_persisted_apply(
        db=db,
        repository_id=repository_id,
        modification_id=modification_id,
        original_content=original_content,
        proposed_content=proposed_content,
    )

    proposal = ProposedModification(
        repository_path=repository_path,
        file_path=file_path,
        original_content=original_content,
        proposed_content=proposed_content,
        diff=diff,
    )

    applied = modification_service.apply_modification(
        proposal
    )

    modification = _persist_applied_modification(
        db=db,
        modification_id=modification_id,
        repository_id=repository_id,
        applied=applied,
    )

    result = {
        "operation": "apply",
        "repository_id": repository_id,
        "applied": True,
        "modification": _serialize_applied_modification(
            applied
        ),
    }

    if modification is not None:
        result.update(
            {
                "modification_id": modification.id,
                "status": modification.status,
            }
        )

    return result


def _rollback_operation(
    db: Session,
    repository_id: int,
    file_path: str,
    original_content: str,
    applied_content: str,
    diff: str = "",
    modification_id: int | None = None,
) -> dict:
    """
    Roll back an applied modification.

    When a persisted modification ID is supplied, the database record
    is validated BEFORE the filesystem is changed.
    """

    repository_path = _get_repository_workspace_path(
        db=db,
        repository_id=repository_id,
    )

    _validate_persisted_rollback(
        db=db,
        repository_id=repository_id,
        modification_id=modification_id,
    )

    modification = AppliedModification(
        repository_path=repository_path,
        file_path=file_path,
        original_content=original_content,
        applied_content=applied_content,
        diff=diff,
    )

    modification_service.rollback_modification(
        modification
    )

    persisted_modification = _persist_rollback(
        db=db,
        modification_id=modification_id,
        repository_id=repository_id,
    )

    result = {
        "operation": "rollback",
        "repository_id": repository_id,
        "rolled_back": True,
        "file_path": file_path,
    }

    if persisted_modification is not None:
        result.update(
            {
                "modification_id": persisted_modification.id,
                "status": persisted_modification.status,
            }
        )

    return result


def prepare_code_modification(
    db: Session,
    repository_id: int,
    modification_request: str,
    limit: int = 5,
    file_path: str | None = None,
    proposed_content: str | None = None,
    operation: str = "context",
    original_content: str | None = None,
    applied_content: str | None = None,
    diff: str = "",
    modification_id: int | None = None,
) -> dict:
    """
    Controlled repository code-modification tool.

    Supported operations:

    context
        Search the repository and prepare relevant code context.

    prepare
        Create a safe modification proposal and persist it when
        a database session exists.

    apply
        Apply an approved modification and persist its state when
        a database session exists.

    rollback
        Restore the original content and persist rollback state
        when a database session and modification ID exist.

    Backward compatibility:
    If file_path and proposed_content are supplied without an
    explicit operation, the operation automatically becomes
    "prepare".
    """

    if not isinstance(
        modification_request,
        str,
    ):
        raise ValueError(
            "modification_request must be a string."
        )

    if not modification_request.strip():
        return {
            "repository_id": repository_id,
            "modification_request": modification_request,
            "matches": [],
            "context": "",
        }

    if (
        operation == "context"
        and (
            file_path is not None
            or proposed_content is not None
        )
    ):
        operation = "prepare"

    if operation not in {
        "context",
        "prepare",
        "apply",
        "rollback",
    }:
        raise ValueError(
            "operation must be one of: "
            "context, prepare, apply, rollback."
        )

    if operation == "prepare":
        if file_path is None:
            raise ValueError(
                "file_path is required for prepare operation."
            )

        if proposed_content is None:
            raise ValueError(
                "proposed_content is required for prepare operation."
            )

        return _prepare_operation(
            db=db,
            repository_id=repository_id,
            file_path=file_path,
            proposed_content=proposed_content,
        )

    if operation == "apply":
        if file_path is None:
            raise ValueError(
                "file_path is required for apply operation."
            )

        if original_content is None:
            raise ValueError(
                "original_content is required for apply operation."
            )

        if proposed_content is None:
            raise ValueError(
                "proposed_content is required for apply operation."
            )

        return _apply_operation(
            db=db,
            repository_id=repository_id,
            file_path=file_path,
            original_content=original_content,
            proposed_content=proposed_content,
            diff=diff,
            modification_id=modification_id,
        )

    if operation == "rollback":
        if file_path is None:
            raise ValueError(
                "file_path is required for rollback operation."
            )

        if original_content is None:
            raise ValueError(
                "original_content is required for rollback operation."
            )

        if applied_content is None:
            raise ValueError(
                "applied_content is required for rollback operation."
            )

        return _rollback_operation(
            db=db,
            repository_id=repository_id,
            file_path=file_path,
            original_content=original_content,
            applied_content=applied_content,
            diff=diff,
            modification_id=modification_id,
        )

    matches = search_code(
        db=db,
        repository_id=repository_id,
        query=modification_request,
        limit=limit,
    )

    return {
        "repository_id": repository_id,
        "modification_request": modification_request,
        "matches": matches,
        "context": _build_context(matches),
    }
