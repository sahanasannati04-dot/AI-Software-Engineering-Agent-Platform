from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.code_modification import CodeModification
from app.models.project import Project
from app.models.repository import Repository
from app.services.modification.post_modification_pipeline import (
    PostModificationPipeline,
)
from app.services.repository.workspace_service import (
    RepositoryWorkspaceService,
)


workspace_service = RepositoryWorkspaceService()


class ModificationValidationService:
    """
    Coordinates persisted code modifications with the
    post-modification validation pipeline.
    """

    def __init__(
        self,
        validation_pipeline: PostModificationPipeline | None = None,
    ):
        self.validation_pipeline = (
            validation_pipeline
            if validation_pipeline is not None
            else PostModificationPipeline()
        )

    def _get_modification(
        self,
        db: Session,
        repository_id: int,
        modification_id: int,
    ) -> CodeModification:
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

    def _get_workspace_path(
        self,
        db: Session,
        repository_id: int,
    ) -> str:
        repository = db.scalar(
            select(Repository)
            .join(Project)
            .where(
                Repository.id == repository_id,
            )
        )

        if not repository:
            raise ValueError(
                "Repository not found."
            )

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

    def validate_applied_modification(
        self,
        db: Session,
        repository_id: int,
        modification_id: int,
        test_target: str | None = None,
    ) -> dict:
        """
        Validate an applied modification by running repository tests.

        Only modifications that are already marked as applied can
        enter the post-modification validation pipeline.
        """

        modification = self._get_modification(
            db=db,
            repository_id=repository_id,
            modification_id=modification_id,
        )

        if modification.status != "applied":
            raise ValueError(
                "Only an applied modification can be validated."
            )

        workspace_path = self._get_workspace_path(
            db=db,
            repository_id=repository_id,
        )

        outcome = self.validation_pipeline.validate_modification(
            workspace_path=workspace_path,
            modification_id=modification_id,
            test_target=test_target,
        )

        result = self.validation_pipeline.build_result(
            outcome
        )

        if outcome.validation.passed:
            modification.status = "validated"
        else:
            modification.status = "validation_failed"

        db.commit()
        db.refresh(modification)

        result.update(
            {
                "repository_id": repository_id,
                "modification_status": modification.status,
                "file_path": modification.file_path,
            }
        )

        return result