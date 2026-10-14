from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.services.repository.git_service import (
    GitRepositoryError,
    GitRepositoryService,
)


def test_clone_timeout_removes_partial_workspace(tmp_path):
    service = GitRepositoryService(
        workspace_root=str(tmp_path)
    )

    workspace_path = tmp_path / "testworkspace"
    workspace_path.mkdir()
    (workspace_path / "partial_file.txt").write_text(
        "partial clone"
    )

    timeout_error = TimeoutError("clone timed out")

    with patch(
        "app.services.repository.git_service.uuid.uuid4",
        return_value=SimpleNamespace(
            hex="testworkspace"
        ),
    ), patch(
        "app.services.repository.git_service.subprocess.run",
        side_effect=__import__(
            "subprocess"
        ).TimeoutExpired(
            cmd=["git", "clone"],
            timeout=300,
        ),
    ):
        with pytest.raises(
            GitRepositoryError,
            match="Git clone operation timed out.",
        ):
            service.clone_repository(
                repository_url="https://github.com/example/repo.git"
            )

    assert not workspace_path.exists()


def test_clone_failure_removes_partial_workspace(tmp_path):
    service = GitRepositoryService(
        workspace_root=str(tmp_path)
    )

    workspace_path = tmp_path / "testworkspace"
    workspace_path.mkdir()
    (workspace_path / "partial_file.txt").write_text(
        "partial clone"
    )

    process_result = SimpleNamespace(
        returncode=128,
        stderr="fatal: repository not found",
        stdout="",
    )

    with patch(
        "app.services.repository.git_service.uuid.uuid4",
        return_value=SimpleNamespace(
            hex="testworkspace"
        ),
    ), patch(
        "app.services.repository.git_service.subprocess.run",
        return_value=process_result,
    ):
        with pytest.raises(
            GitRepositoryError,
            match="Git clone failed: fatal: repository not found",
        ):
            service.clone_repository(
                repository_url="https://github.com/example/repo.git"
            )

    assert not workspace_path.exists()


def test_successful_clone_returns_workspace_information(tmp_path):
    service = GitRepositoryService(
        workspace_root=str(tmp_path)
    )

    process_result = SimpleNamespace(
        returncode=0,
        stderr="",
        stdout="",
    )

    with patch(
        "app.services.repository.git_service.uuid.uuid4",
        return_value=SimpleNamespace(
            hex="testworkspace"
        ),
    ), patch(
        "app.services.repository.git_service.subprocess.run",
        return_value=process_result,
    ) as mock_run:
        workspace_id, repository_path = (
            service.clone_repository(
                repository_url="https://github.com/example/repo.git",
                branch="main",
            )
        )

    assert workspace_id == "testworkspace"
    assert repository_path == (
        Path(tmp_path) / "testworkspace"
    )

    mock_run.assert_called_once()