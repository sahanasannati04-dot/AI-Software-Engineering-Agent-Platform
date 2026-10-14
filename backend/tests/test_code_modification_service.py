from pathlib import Path

import pytest

from app.services.tools.code_modification_service import (
    AppliedModification,
    CodeModificationConflictError,
    CodeModificationFileError,
    CodeModificationService,
    CodeModificationValidationError,
)


@pytest.fixture
def service():
    return CodeModificationService()


@pytest.fixture
def repository(tmp_path):
    repository_path = tmp_path / "repository"
    repository_path.mkdir()

    (repository_path / "app.py").write_text(
        "def hello():\n"
        "    return 'hello'\n",
        encoding="utf-8",
    )

    return repository_path


def test_read_file_returns_repository_file_content(
    service,
    repository,
):
    content = service.read_file(
        repository_path=str(repository),
        file_path="app.py",
    )

    assert content == (
        "def hello():\n"
        "    return 'hello'\n"
    )


def test_prepare_modification_generates_diff_without_writing_file(
    service,
    repository,
):
    proposed_content = (
        "def hello():\n"
        "    return 'hello world'\n"
    )

    result = service.prepare_modification(
        repository_path=str(repository),
        file_path="app.py",
        proposed_content=proposed_content,
    )

    assert result.original_content == (
        "def hello():\n"
        "    return 'hello'\n"
    )

    assert result.proposed_content == proposed_content
    assert result.diff != ""
    assert "-    return 'hello'" in result.diff
    assert "+    return 'hello world'" in result.diff

    actual_content = (
        repository / "app.py"
    ).read_text(encoding="utf-8")

    assert actual_content == result.original_content


def test_identical_content_produces_empty_diff(
    service,
    repository,
):
    original_content = (
        repository / "app.py"
    ).read_text(encoding="utf-8")

    result = service.prepare_modification(
        repository_path=str(repository),
        file_path="app.py",
        proposed_content=original_content,
    )

    assert result.diff == ""

    actual_content = (
        repository / "app.py"
    ).read_text(encoding="utf-8")

    assert actual_content == original_content


def test_rejects_absolute_file_path(
    service,
    repository,
):
    with pytest.raises(
        CodeModificationValidationError,
        match="file_path must be relative",
    ):
        service.read_file(
            repository_path=str(repository),
            file_path=str(
                Path(repository) / "app.py"
            ),
        )


def test_rejects_path_traversal(
    service,
    repository,
):
    with pytest.raises(
        CodeModificationValidationError,
        match="must remain inside the repository",
    ):
        service.read_file(
            repository_path=str(repository),
            file_path="../outside.py",
        )


def test_rejects_nested_path_traversal(
    service,
    repository,
):
    nested_directory = repository / "nested"
    nested_directory.mkdir()

    with pytest.raises(
        CodeModificationValidationError,
        match="must remain inside the repository",
    ):
        service.read_file(
            repository_path=str(repository),
            file_path="nested/../../outside.py",
        )


def test_rejects_missing_repository(
    service,
    tmp_path,
):
    missing_repository = (
        tmp_path / "does-not-exist"
    )

    with pytest.raises(
        CodeModificationFileError,
        match="Repository path does not exist",
    ):
        service.read_file(
            repository_path=str(missing_repository),
            file_path="app.py",
        )


def test_rejects_missing_file(
    service,
    repository,
):
    with pytest.raises(
        CodeModificationFileError,
        match="Target file does not exist",
    ):
        service.read_file(
            repository_path=str(repository),
            file_path="missing.py",
        )


def test_rejects_directory_as_file(
    service,
    repository,
):
    directory = repository / "folder"
    directory.mkdir()

    with pytest.raises(
        CodeModificationFileError,
        match="Target path is not a file",
    ):
        service.read_file(
            repository_path=str(repository),
            file_path="folder",
        )


def test_rejects_empty_repository_path(
    service,
):
    with pytest.raises(
        CodeModificationValidationError,
        match="repository_path is required",
    ):
        service.read_file(
            repository_path="",
            file_path="app.py",
        )


def test_rejects_empty_file_path(
    service,
    repository,
):
    with pytest.raises(
        CodeModificationValidationError,
        match="file_path is required",
    ):
        service.read_file(
            repository_path=str(repository),
            file_path="",
        )


def test_rejects_null_character_in_file_path(
    service,
    repository,
):
    with pytest.raises(
        CodeModificationValidationError,
        match="invalid character",
    ):
        service.read_file(
            repository_path=str(repository),
            file_path="app\x00.py",
        )


def test_rejects_non_string_proposed_content(
    service,
    repository,
):
    with pytest.raises(
        CodeModificationValidationError,
        match="proposed_content must be a string",
    ):
        service.prepare_modification(
            repository_path=str(repository),
            file_path="app.py",
            proposed_content=None,
        )


def test_generate_diff_returns_expected_unified_diff(
    service,
):
    original = (
        "line one\n"
        "line two\n"
    )

    proposed = (
        "line one\n"
        "line changed\n"
    )

    diff = service.generate_diff(
        file_path="example.py",
        original_content=original,
        proposed_content=proposed,
    )

    assert "--- a/example.py" in diff
    assert "+++ b/example.py" in diff
    assert "-line two" in diff
    assert "+line changed" in diff


def test_apply_modification_changes_file(
    service,
    repository,
):
    proposed_content = (
        "def hello():\n"
        "    return 'hello world'\n"
    )

    proposal = service.prepare_modification(
        repository_path=str(repository),
        file_path="app.py",
        proposed_content=proposed_content,
    )

    result = service.apply_modification(proposal)

    assert isinstance(
        result,
        AppliedModification,
    )

    assert result.original_content == (
        "def hello():\n"
        "    return 'hello'\n"
    )

    assert result.applied_content == proposed_content

    actual_content = (
        repository / "app.py"
    ).read_text(encoding="utf-8")

    assert actual_content == proposed_content


def test_apply_modification_preserves_diff(
    service,
    repository,
):
    proposed_content = (
        "def hello():\n"
        "    return 'changed'\n"
    )

    proposal = service.prepare_modification(
        repository_path=str(repository),
        file_path="app.py",
        proposed_content=proposed_content,
    )

    result = service.apply_modification(proposal)

    assert result.diff == proposal.diff
    assert "-    return 'hello'" in result.diff
    assert "+    return 'changed'" in result.diff


def test_apply_modification_detects_concurrent_change(
    service,
    repository,
):
    proposal = service.prepare_modification(
        repository_path=str(repository),
        file_path="app.py",
        proposed_content=(
            "def hello():\n"
            "    return 'agent change'\n"
        ),
    )

    (
        repository / "app.py"
    ).write_text(
        "def hello():\n"
        "    return 'another developer change'\n",
        encoding="utf-8",
    )

    with pytest.raises(
        CodeModificationConflictError,
        match="Target file changed",
    ):
        service.apply_modification(proposal)

    actual_content = (
        repository / "app.py"
    ).read_text(encoding="utf-8")

    assert "another developer change" in actual_content


def test_rollback_restores_original_content(
    service,
    repository,
):
    original_content = (
        repository / "app.py"
    ).read_text(encoding="utf-8")

    proposed_content = (
        "def hello():\n"
        "    return 'modified'\n"
    )

    proposal = service.prepare_modification(
        repository_path=str(repository),
        file_path="app.py",
        proposed_content=proposed_content,
    )

    applied = service.apply_modification(proposal)

    assert (
        repository / "app.py"
    ).read_text(encoding="utf-8") == proposed_content

    service.rollback_modification(applied)

    restored_content = (
        repository / "app.py"
    ).read_text(encoding="utf-8")

    assert restored_content == original_content


def test_rollback_detects_newer_change(
    service,
    repository,
):
    proposal = service.prepare_modification(
        repository_path=str(repository),
        file_path="app.py",
        proposed_content=(
            "def hello():\n"
            "    return 'agent change'\n"
        ),
    )

    applied = service.apply_modification(proposal)

    (
        repository / "app.py"
    ).write_text(
        "def hello():\n"
        "    return 'newer change'\n",
        encoding="utf-8",
    )

    with pytest.raises(
        CodeModificationConflictError,
        match="Rollback was not performed",
    ):
        service.rollback_modification(applied)

    actual_content = (
        repository / "app.py"
    ).read_text(encoding="utf-8")

    assert "newer change" in actual_content


def test_apply_identical_content_does_not_change_file(
    service,
    repository,
):
    original_content = (
        repository / "app.py"
    ).read_text(encoding="utf-8")

    proposal = service.prepare_modification(
        repository_path=str(repository),
        file_path="app.py",
        proposed_content=original_content,
    )

    result = service.apply_modification(proposal)

    assert result.diff == ""
    assert result.applied_content == original_content

    actual_content = (
        repository / "app.py"
    ).read_text(encoding="utf-8")

    assert actual_content == original_content