from unittest.mock import Mock

import pytest

from app.services.execution_service import (
    RepositoryTestExecutionService,
)
from app.services.sandbox.sandbox_service import (
    SandboxConfigurationError,
    SandboxResult,
)


def test_build_test_command_without_target():
    service = RepositoryTestExecutionService()

    command = service.build_test_command()

    assert command == [
        "python",
        "-m",
        "pytest",
    ]


def test_build_test_command_with_target():
    service = RepositoryTestExecutionService()

    command = service.build_test_command(
        test_target="tests/test_example.py",
    )

    assert command == [
        "python",
        "-m",
        "pytest",
        "tests/test_example.py",
    ]


def test_execute_tests_returns_passed_result():
    sandbox = Mock()

    sandbox.execute.return_value = SandboxResult(
        exit_code=0,
        stdout="5 passed",
        stderr="",
        timed_out=False,
    )

    service = RepositoryTestExecutionService(
        sandbox_service=sandbox,
    )

    result = service.execute_tests(
        workspace_path="workspace/test",
    )

    assert result.command == [
        "python",
        "-m",
        "pytest",
    ]
    assert result.exit_code == 0
    assert result.stdout == "5 passed"
    assert result.stderr == ""
    assert result.passed is True
    assert result.timed_out is False

    sandbox.execute.assert_called_once_with(
        command=[
            "python",
            "-m",
            "pytest",
        ],
        workspace_path="workspace/test",
    )


def test_execute_tests_returns_failed_result():
    sandbox = Mock()

    sandbox.execute.return_value = SandboxResult(
        exit_code=1,
        stdout="2 failed",
        stderr="AssertionError",
        timed_out=False,
    )

    service = RepositoryTestExecutionService(
        sandbox_service=sandbox,
    )

    result = service.execute_tests(
        workspace_path="workspace/test",
        test_target="tests/test_example.py",
    )

    assert result.exit_code == 1
    assert result.stdout == "2 failed"
    assert result.stderr == "AssertionError"
    assert result.passed is False
    assert result.timed_out is False


def test_execute_tests_returns_timeout_result():
    sandbox = Mock()

    sandbox.execute.return_value = SandboxResult(
        exit_code=124,
        stdout="",
        stderr="Execution timed out",
        timed_out=True,
    )

    service = RepositoryTestExecutionService(
        sandbox_service=sandbox,
    )

    result = service.execute_tests(
        workspace_path="workspace/test",
    )

    assert result.exit_code == 124
    assert result.passed is False
    assert result.timed_out is True


def test_execute_tests_propagates_sandbox_errors():
    sandbox = Mock()

    sandbox.execute.side_effect = SandboxConfigurationError(
        "Docker sandbox runtime is not available."
    )

    service = RepositoryTestExecutionService(
        sandbox_service=sandbox,
    )

    with pytest.raises(
        SandboxConfigurationError,
        match="Docker sandbox runtime is not available.",
    ):
        service.execute_tests(
            workspace_path="workspace/test",
        )
