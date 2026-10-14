from pathlib import Path
from unittest.mock import patch

import pytest

from app.models.code_modification import CodeModification
from app.models.project import Project
from app.models.repository import Repository
from app.models.user import User
from app.services.tools.code_modification_tool import (
    prepare_code_modification,
)


def _create_repository(
    db_session,
    workspace_id: str,
    suffix: str = "",
) -> Repository:
    user = User(
        email=f"modification-persistence{suffix}@test.local",
        full_name="Modification Persistence Test User",
        hashed_password="test-password-hash",
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    project = Project(
        name=f"Modification Persistence Test Project{suffix}",
        description="Test project for code modification persistence.",
        owner_id=user.id,
    )

    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    repository = Repository(
        name=f"Modification Persistence Test Repository{suffix}",
        url=f"https://github.com/example/test-repository{suffix}.git",
        default_branch="main",
        language="Python",
        status="ready",
        workspace_id=workspace_id,
        project_id=project.id,
    )

    db_session.add(repository)
    db_session.commit()
    db_session.refresh(repository)

    return repository


def test_prepare_persists_modification(
    db_session,
    tmp_path: Path,
):
    target_file = tmp_path / "app.py"

    original_content = (
        "def hello():\n"
        "    return 'hello'\n"
    )

    proposed_content = (
        "def hello():\n"
        "    return 'hello world'\n"
    )

    target_file.write_text(
        original_content,
        encoding="utf-8",
    )

    repository = _create_repository(
        db_session=db_session,
        workspace_id=tmp_path.name,
    )

    with patch(
        "app.services.tools.code_modification_tool."
        "_get_repository_workspace_path",
        return_value=str(tmp_path),
    ):
        result = prepare_code_modification(
            db=db_session,
            repository_id=repository.id,
            modification_request="Change hello response.",
            file_path="app.py",
            proposed_content=proposed_content,
        )

    assert result["operation"] == "prepare"
    assert result["status"] == "prepared"
    assert result["approval_required"] is True
    assert result["modification_id"] is not None

    modification = db_session.get(
        CodeModification,
        result["modification_id"],
    )

    assert modification is not None
    assert modification.repository_id == repository.id
    assert modification.file_path == "app.py"
    assert modification.status == "prepared"
    assert modification.original_content == original_content
    assert modification.proposed_content == proposed_content
    assert modification.applied_content is None
    assert modification.approval_required is True

    assert target_file.read_text(
        encoding="utf-8",
    ) == original_content


def test_apply_updates_persisted_modification(
    db_session,
    tmp_path: Path,
):
    target_file = tmp_path / "app.py"

    original_content = "old\n"
    proposed_content = "new\n"

    target_file.write_text(
        original_content,
        encoding="utf-8",
    )

    repository = _create_repository(
        db_session=db_session,
        workspace_id=tmp_path.name,
    )

    with patch(
        "app.services.tools.code_modification_tool."
        "_get_repository_workspace_path",
        return_value=str(tmp_path),
    ):
        prepared = prepare_code_modification(
            db=db_session,
            repository_id=repository.id,
            modification_request="Change app.py.",
            file_path="app.py",
            proposed_content=proposed_content,
        )

    modification_id = prepared["modification_id"]

    with patch(
        "app.services.tools.code_modification_tool."
        "_get_repository_workspace_path",
        return_value=str(tmp_path),
    ):
        result = prepare_code_modification(
            db=db_session,
            repository_id=repository.id,
            modification_request="Apply prepared change.",
            operation="apply",
            file_path="app.py",
            original_content=original_content,
            proposed_content=proposed_content,
            modification_id=modification_id,
        )

    assert result["operation"] == "apply"
    assert result["applied"] is True
    assert result["status"] == "applied"
    assert result["modification_id"] == modification_id

    modification = db_session.get(
        CodeModification,
        modification_id,
    )

    assert modification is not None
    assert modification.status == "applied"
    assert modification.applied_content == proposed_content
    assert modification.approved_at is not None
    assert modification.applied_at is not None

    assert target_file.read_text(
        encoding="utf-8",
    ) == proposed_content


def test_rollback_updates_persisted_modification(
    db_session,
    tmp_path: Path,
):
    target_file = tmp_path / "app.py"

    original_content = "old\n"
    proposed_content = "new\n"

    target_file.write_text(
        proposed_content,
        encoding="utf-8",
    )

    repository = _create_repository(
        db_session=db_session,
        workspace_id=tmp_path.name,
    )

    modification = CodeModification(
        repository_id=repository.id,
        file_path="app.py",
        status="applied",
        original_content=original_content,
        proposed_content=proposed_content,
        applied_content=proposed_content,
        diff="-old\n+new\n",
        approval_required=False,
    )

    db_session.add(modification)
    db_session.commit()
    db_session.refresh(modification)

    modification_id = modification.id

    with patch(
        "app.services.tools.code_modification_tool."
        "_get_repository_workspace_path",
        return_value=str(tmp_path),
    ):
        result = prepare_code_modification(
            db=db_session,
            repository_id=repository.id,
            modification_request="Rollback app.py.",
            operation="rollback",
            file_path="app.py",
            original_content=original_content,
            applied_content=proposed_content,
            modification_id=modification_id,
        )

    assert result["operation"] == "rollback"
    assert result["rolled_back"] is True
    assert result["status"] == "rolled_back"
    assert result["modification_id"] == modification_id

    assert target_file.read_text(
        encoding="utf-8",
    ) == original_content

    persisted = db_session.get(
        CodeModification,
        modification_id,
    )

    assert persisted is not None
    assert persisted.status == "rolled_back"
    assert persisted.rolled_back_at is not None


def test_apply_rejects_unknown_modification_id(
    db_session,
    tmp_path: Path,
):
    target_file = tmp_path / "app.py"

    original_content = "old\n"
    proposed_content = "new\n"

    target_file.write_text(
        original_content,
        encoding="utf-8",
    )

    repository = _create_repository(
        db_session=db_session,
        workspace_id=tmp_path.name,
    )

    with patch(
        "app.services.tools.code_modification_tool."
        "_get_repository_workspace_path",
        return_value=str(tmp_path),
    ):
        with pytest.raises(
            ValueError,
            match="Code modification record not found",
        ):
            prepare_code_modification(
                db=db_session,
                repository_id=repository.id,
                modification_request="Apply unknown change.",
                operation="apply",
                file_path="app.py",
                original_content=original_content,
                proposed_content=proposed_content,
                modification_id=999999,
            )

    assert target_file.read_text(
        encoding="utf-8",
    ) == original_content


def test_rollback_rejects_unknown_modification_id(
    db_session,
    tmp_path: Path,
):
    target_file = tmp_path / "app.py"

    original_content = "old\n"
    proposed_content = "new\n"

    target_file.write_text(
        proposed_content,
        encoding="utf-8",
    )

    repository = _create_repository(
        db_session=db_session,
        workspace_id=tmp_path.name,
    )

    with patch(
        "app.services.tools.code_modification_tool."
        "_get_repository_workspace_path",
        return_value=str(tmp_path),
    ):
        with pytest.raises(
            ValueError,
            match="Code modification record not found",
        ):
            prepare_code_modification(
                db=db_session,
                repository_id=repository.id,
                modification_request="Rollback unknown change.",
                operation="rollback",
                file_path="app.py",
                original_content=original_content,
                applied_content=proposed_content,
                modification_id=999999,
            )

    assert target_file.read_text(
        encoding="utf-8",
    ) == proposed_content


def test_apply_rejects_modification_from_different_repository(
    db_session,
    tmp_path: Path,
):
    repository_one_path = tmp_path / "repository_one"
    repository_two_path = tmp_path / "repository_two"

    repository_one_path.mkdir()
    repository_two_path.mkdir()

    file_one = repository_one_path / "app.py"
    file_two = repository_two_path / "app.py"

    original_content = "old\n"
    proposed_content = "new\n"

    file_one.write_text(
        original_content,
        encoding="utf-8",
    )

    file_two.write_text(
        original_content,
        encoding="utf-8",
    )

    repository_one = _create_repository(
        db_session=db_session,
        workspace_id=repository_one_path.name,
        suffix="-one",
    )

    repository_two = _create_repository(
        db_session=db_session,
        workspace_id=repository_two_path.name,
        suffix="-two",
    )

    with patch(
        "app.services.tools.code_modification_tool."
        "_get_repository_workspace_path",
        return_value=str(repository_one_path),
    ):
        prepared = prepare_code_modification(
            db=db_session,
            repository_id=repository_one.id,
            modification_request="Change app.py.",
            file_path="app.py",
            proposed_content=proposed_content,
        )

    modification_id = prepared["modification_id"]

    with patch(
        "app.services.tools.code_modification_tool."
        "_get_repository_workspace_path",
        return_value=str(repository_two_path),
    ):
        with pytest.raises(
            ValueError,
            match="Code modification record not found",
        ):
            prepare_code_modification(
                db=db_session,
                repository_id=repository_two.id,
                modification_request="Apply another repository change.",
                operation="apply",
                file_path="app.py",
                original_content=original_content,
                proposed_content=proposed_content,
                modification_id=modification_id,
            )

    assert file_one.read_text(
        encoding="utf-8",
    ) == original_content

    assert file_two.read_text(
        encoding="utf-8",
    ) == original_content

    persisted = db_session.get(
        CodeModification,
        modification_id,
    )

    assert persisted is not None
    assert persisted.repository_id == repository_one.id
    assert persisted.status == "prepared"


def test_rollback_rejects_non_applied_modification(
    db_session,
    tmp_path: Path,
):
    target_file = tmp_path / "app.py"

    original_content = "old\n"
    proposed_content = "new\n"

    target_file.write_text(
        original_content,
        encoding="utf-8",
    )

    repository = _create_repository(
        db_session=db_session,
        workspace_id=tmp_path.name,
    )

    with patch(
        "app.services.tools.code_modification_tool."
        "_get_repository_workspace_path",
        return_value=str(tmp_path),
    ):
        prepared = prepare_code_modification(
            db=db_session,
            repository_id=repository.id,
            modification_request="Prepare app.py change.",
            file_path="app.py",
            proposed_content=proposed_content,
        )

    modification_id = prepared["modification_id"]

    with patch(
        "app.services.tools.code_modification_tool."
        "_get_repository_workspace_path",
        return_value=str(tmp_path),
    ):
        with pytest.raises(
            ValueError,
            match="Only an applied modification can be rolled back",
        ):
            prepare_code_modification(
                db=db_session,
                repository_id=repository.id,
                modification_request="Rollback prepared change.",
                operation="rollback",
                file_path="app.py",
                original_content=original_content,
                applied_content=proposed_content,
                modification_id=modification_id,
            )

    persisted = db_session.get(
        CodeModification,
        modification_id,
    )

    assert persisted is not None
    assert persisted.status == "prepared"

    assert target_file.read_text(
        encoding="utf-8",
    ) == original_content