from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from app.services.tools.test_execution_tool import (
    ExecutionToolError,
    prepare_test_execution,
)


def test_prepare_test_execution_rejects_empty_repository_path():
    with pytest.raises(
        ExecutionToolError,
        match="repository_path is required.",
    ):
        prepare_test_execution(
            repository_path="",
        )


def test_prepare_test_execution_rejects_non_string_repository_path():
    with pytest.raises(
        ExecutionToolError,
        match="repository_path must be a string.",
    ):
        prepare_test_execution(
            repository_path=None,
        )


def test_prepare_test_execution_rejects_missing_repository_path(
    tmp_path: Path,
):
    missing_path = tmp_path / "missing-repository"

    with pytest.raises(
        ExecutionToolError,
        match="Repository path does not exist.",
    ):
        prepare_test_execution(
            repository_path=str(missing_path),
        )


def test_prepare_test_execution_rejects_file_as_repository_path(
    tmp_path: Path,
):
    repository_file = tmp_path / "repository.txt"

    repository_file.write_text(
        "not a directory",
        encoding="utf-8",
    )

    with pytest.raises(
        ExecutionToolError,
        match="Repository path must be a directory.",
    ):
        prepare_test_execution(
            repository_path=str(repository_file),
        )


def test_prepare_test_execution_rejects_invalid_test_target(
    tmp_path: Path,
):
    with pytest.raises(
        ExecutionToolError,
        match="test_target must be a string.",
    ):
        prepare_test_execution(
            repository_path=str(tmp_path),
            test_target=123,
        )


def test_prepare_test_execution_rejects_null_character(
    tmp_path: Path,
):
    with pytest.raises(
        ExecutionToolError,
        match="test_target contains an invalid character.",
    ):
        prepare_test_execution(
            repository_path=str(tmp_path),
            test_target="tests/test_api.py\x00",
        )


def test_prepare_test_execution_allows_empty_test_target(
    tmp_path: Path,
):
    mock_result = Mock()

    mock_result.command = [
        "python",
        "-m",
        "pytest",
    ]
    mock_result.exit_code = 0
    mock_result.stdout = "5 passed"
    mock_result.stderr = ""
    mock_result.passed = True
    mock_result.timed_out = False

    mock_service = Mock()
    mock_service.execute_tests.return_value = mock_result

    with patch(
        "app.services.tools.test_execution_tool.RepositoryTestExecutionService",
        return_value=mock_service,
    ):
        result = prepare_test_execution(
            repository_path=str(tmp_path),
            test_target="   ",
        )

    assert result == {
        "command": [
            "python",
            "-m",
            "pytest",
        ],
        "exit_code": 0,
        "stdout": "5 passed",
        "stderr": "",
        "passed": True,
        "timed_out": False,
    }

    mock_service.execute_tests.assert_called_once_with(
        workspace_path=str(tmp_path.resolve()),
        test_target=None,
    )


def test_prepare_test_execution_returns_success_result(
    tmp_path: Path,
):
    mock_result = Mock()

    mock_result.command = [
        "python",
        "-m",
        "pytest",
    ]
    mock_result.exit_code = 0
    mock_result.stdout = "5 passed"
    mock_result.stderr = ""
    mock_result.passed = True
    mock_result.timed_out = False

    mock_service = Mock()
    mock_service.execute_tests.return_value = mock_result

    with patch(
        "app.services.tools.test_execution_tool.RepositoryTestExecutionService",
        return_value=mock_service,
    ):
        result = prepare_test_execution(
            repository_path=str(tmp_path),
        )

    assert result == {
        "command": [
            "python",
            "-m",
            "pytest",
        ],
        "exit_code": 0,
        "stdout": "5 passed",
        "stderr": "",
        "passed": True,
        "timed_out": False,
    }

    mock_service.execute_tests.assert_called_once_with(
        workspace_path=str(tmp_path.resolve()),
        test_target=None,
    )


def test_prepare_test_execution_passes_test_target(
    tmp_path: Path,
):
    mock_result = Mock()

    mock_result.command = [
        "python",
        "-m",
        "pytest",
        "tests/test_api.py",
    ]
    mock_result.exit_code = 0
    mock_result.stdout = "3 passed"
    mock_result.stderr = ""
    mock_result.passed = True
    mock_result.timed_out = False

    mock_service = Mock()
    mock_service.execute_tests.return_value = mock_result

    with patch(
        "app.services.tools.test_execution_tool.RepositoryTestExecutionService",
        return_value=mock_service,
    ):
        result = prepare_test_execution(
            repository_path=str(tmp_path),
            test_target="tests/test_api.py",
        )

    assert result["passed"] is True
    assert result["exit_code"] == 0

    mock_service.execute_tests.assert_called_once_with(
        workspace_path=str(tmp_path.resolve()),
        test_target="tests/test_api.py",
    )


def test_prepare_test_execution_returns_failed_result(
    tmp_path: Path,
):
    mock_result = Mock()

    mock_result.command = [
        "python",
        "-m",
        "pytest",
    ]
    mock_result.exit_code = 1
    mock_result.stdout = "1 failed"
    mock_result.stderr = "AssertionError"
    mock_result.passed = False
    mock_result.timed_out = False

    mock_service = Mock()
    mock_service.execute_tests.return_value = mock_result

    with patch(
        "app.services.tools.test_execution_tool.RepositoryTestExecutionService",
        return_value=mock_service,
    ):
        result = prepare_test_execution(
            repository_path=str(tmp_path),
        )

    assert result["passed"] is False
    assert result["exit_code"] == 1
    assert result["stderr"] == "AssertionError"


def test_prepare_test_execution_returns_timeout_result(
    tmp_path: Path,
):
    mock_result = Mock()

    mock_result.command = [
        "python",
        "-m",
        "pytest",
    ]
    mock_result.exit_code = 124
    mock_result.stdout = ""
    mock_result.stderr = "Execution timed out"
    mock_result.passed = False
    mock_result.timed_out = True

    mock_service = Mock()
    mock_service.execute_tests.return_value = mock_result

    with patch(
        "app.services.tools.test_execution_tool.RepositoryTestExecutionService",
        return_value=mock_service,
    ):
        result = prepare_test_execution(
            repository_path=str(tmp_path),
        )

    assert result["passed"] is False
    assert result["timed_out"] is True
    assert result["exit_code"] == 124