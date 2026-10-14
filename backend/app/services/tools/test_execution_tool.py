from pathlib import Path

from app.services.execution_service import (
    RepositoryTestExecutionService,
)


class ExecutionToolError(Exception):
    """
    Raised when test execution input is invalid.
    """


def _validate_repository_path(
    repository_path: str,
) -> str:
    if not isinstance(repository_path, str):
        raise ExecutionToolError(
            "repository_path must be a string."
        )

    repository_path = repository_path.strip()

    if not repository_path:
        raise ExecutionToolError(
            "repository_path is required."
        )

    path = Path(repository_path)

    if not path.exists():
        raise ExecutionToolError(
            "Repository path does not exist."
        )

    if not path.is_dir():
        raise ExecutionToolError(
            "Repository path must be a directory."
        )

    return str(path.resolve())


def _validate_test_target(
    test_target: str | None,
) -> str | None:
    if test_target is None:
        return None

    if not isinstance(test_target, str):
        raise ExecutionToolError(
            "test_target must be a string."
        )

    test_target = test_target.strip()

    if not test_target:
        return None

    if "\x00" in test_target:
        raise ExecutionToolError(
            "test_target contains an invalid character."
        )

    return test_target


def prepare_test_execution(
    repository_path: str,
    test_target: str | None = None,
) -> dict:
    """
    Validate repository test execution input and execute
    repository tests through the sandbox service.
    """

    validated_repository_path = _validate_repository_path(
        repository_path
    )

    validated_test_target = _validate_test_target(
        test_target
    )

    service = RepositoryTestExecutionService()

    result = service.execute_tests(
        workspace_path=validated_repository_path,
        test_target=validated_test_target,
    )

    return {
        "command": result.command,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "passed": result.passed,
        "timed_out": result.timed_out,
    }