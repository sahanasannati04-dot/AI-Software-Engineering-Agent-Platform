from dataclasses import dataclass

from app.services.execution_service import (
    RepositoryTestExecutionService,
)


@dataclass
class ValidationResult:
    """
    Structured result of post-modification validation.
    """

    passed: bool
    exit_code: int
    command: list[str]
    stdout: str
    stderr: str
    timed_out: bool
    status: str


class PostModificationValidationService:
    """
    Runs automated tests after a code modification and classifies
    the resulting validation state.
    """

    def __init__(
        self,
        test_execution_service: RepositoryTestExecutionService | None = None,
    ):
        self.test_execution_service = (
            test_execution_service
            if test_execution_service is not None
            else RepositoryTestExecutionService()
        )

    def validate(
        self,
        workspace_path: str,
        test_target: str | None = None,
    ) -> ValidationResult:
        result = self.test_execution_service.execute_tests(
            workspace_path=workspace_path,
            test_target=test_target,
        )

        if result.passed:
            status = "passed"
        elif result.timed_out:
            status = "timeout"
        else:
            status = "failed"

        return ValidationResult(
            passed=result.passed,
            exit_code=result.exit_code,
            command=result.command,
            stdout=result.stdout,
            stderr=result.stderr,
            timed_out=result.timed_out,
            status=status,
        )