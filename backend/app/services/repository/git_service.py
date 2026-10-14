import shutil
import subprocess
import uuid
from pathlib import Path


class GitRepositoryError(Exception):
    """Raised when a Git repository operation fails."""


class GitRepositoryService:
    """
    Service responsible for Git repository operations.
    """

    def __init__(
        self,
        workspace_root: str = "workspace",
    ):
        self.workspace_root = Path(workspace_root)

    def get_repository_path(
        self,
        workspace_id: str,
    ) -> Path:
        return self.workspace_root / workspace_id

    def clone_repository(
        self,
        repository_url: str,
        branch: str = "main",
        timeout: int = 300,
    ) -> tuple[str, Path]:
        workspace_id = uuid.uuid4().hex
        repository_path = self.get_repository_path(
            workspace_id
        )

        self.workspace_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        command = [
            "git",
            "clone",
            "--branch",
            branch,
            "--single-branch",
            repository_url,
            str(repository_path),
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )

        except subprocess.TimeoutExpired as exc:
            # A timed-out clone can leave a partially created
            # workspace behind. Always remove it.
            if repository_path.exists():
                self._remove_workspace(
                    repository_path
                )

            raise GitRepositoryError(
                "Git clone operation timed out."
            ) from exc

        if result.returncode != 0:
            if repository_path.exists():
                self._remove_workspace(
                    repository_path
                )

            error_message = result.stderr.strip()

            if not error_message:
                error_message = (
                    "Git clone exited with a non-zero status."
                )

            raise GitRepositoryError(
                f"Git clone failed: {error_message}"
            )

        return workspace_id, repository_path

    def _remove_workspace(
        self,
        repository_path: Path,
    ) -> None:
        shutil.rmtree(
            repository_path,
            ignore_errors=True,
        )