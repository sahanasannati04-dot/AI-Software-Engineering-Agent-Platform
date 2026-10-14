from pathlib import Path

from app.services.repository.git_service import (
    GitRepositoryService,
)


class RepositoryWorkspaceService:
    """
    Service responsible for repository workspace operations.
    """

    def __init__(
        self,
        git_service: GitRepositoryService | None = None,
    ):
        self.git_service = (
            git_service
            if git_service is not None
            else GitRepositoryService()
        )

    def clone_repository(
        self,
        repository_url: str,
        branch: str = "main",
    ) -> tuple[str, Path]:
        return self.git_service.clone_repository(
            repository_url=repository_url,
            branch=branch,
        )

    def get_workspace_path(
        self,
        workspace_id: str,
    ) -> Path:
        return self.git_service.get_repository_path(
            workspace_id
        )

    def workspace_exists(
        self,
        workspace_id: str,
    ) -> bool:
        workspace_path = self.get_workspace_path(
            workspace_id
        )

        return workspace_path.exists()

    def verify_workspace(
        self,
        workspace_id: str,
    ) -> bool:
        workspace_path = self.get_workspace_path(
            workspace_id
        )

        if not workspace_path.exists():
            return False

        return (
            workspace_path / ".git"
        ).exists()

    def delete_workspace(
        self,
        workspace_id: str,
    ) -> bool:
        workspace_path = self.get_workspace_path(
            workspace_id
        )

        if not workspace_path.exists():
            return False

        self.git_service._remove_workspace(
            workspace_path
        )

        return not workspace_path.exists()
