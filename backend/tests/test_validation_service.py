from unittest.mock import Mock

from app.services.validation.validation_service import (
    PostModificationValidationService,
)


def test_validation_passed():
    execution_service = Mock()

    execution_service.execute_tests.return_value = Mock(
        passed=True,
        exit_code=0,
        command=["python", "-m", "pytest"],
        stdout="3 passed",
        stderr="",
        timed_out=False,
    )

    service = PostModificationValidationService(
        test_execution_service=execution_service,
    )

    result = service.validate(
        workspace_path="C:\\workspace",
    )

    assert result.passed is True
    assert result.status == "passed"
    assert result.exit_code == 0
    assert result.timed_out is False
    assert result.stdout == "3 passed"


def test_validation_failed():
    execution_service = Mock()

    execution_service.execute_tests.return_value = Mock(
        passed=False,
        exit_code=1,
        command=["python", "-m", "pytest"],
        stdout="",
        stderr="AssertionError",
        timed_out=False,
    )

    service = PostModificationValidationService(
        test_execution_service=execution_service,
    )

    result = service.validate(
        workspace_path="C:\\workspace",
    )

    assert result.passed is False
    assert result.status == "failed"
    assert result.exit_code == 1
    assert result.timed_out is False
    assert result.stderr == "AssertionError"


def test_validation_timeout():
    execution_service = Mock()

    execution_service.execute_tests.return_value = Mock(
        passed=False,
        exit_code=-1,
        command=["python", "-m", "pytest"],
        stdout="",
        stderr="Test execution timed out",
        timed_out=True,
    )

    service = PostModificationValidationService(
        test_execution_service=execution_service,
    )

    result = service.validate(
        workspace_path="C:\\workspace",
    )

    assert result.passed is False
    assert result.status == "timeout"
    assert result.timed_out is True
    assert result.exit_code == -1


def test_validation_passes_test_target():
    execution_service = Mock()

    execution_service.execute_tests.return_value = Mock(
        passed=True,
        exit_code=0,
        command=[
            "python",
            "-m",
            "pytest",
            "tests/test_example.py",
        ],
        stdout="1 passed",
        stderr="",
        timed_out=False,
    )

    service = PostModificationValidationService(
        test_execution_service=execution_service,
    )

    result = service.validate(
        workspace_path="C:\\workspace",
        test_target="tests/test_example.py",
    )

    execution_service.execute_tests.assert_called_once_with(
        workspace_path="C:\\workspace",
        test_target="tests/test_example.py",
    )

    assert result.passed is True
    assert result.status == "passed"