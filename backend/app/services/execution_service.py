from dataclasses import dataclass

from app.services.sandbox.docker_sandbox import DockerSandbox
from app.services.sandbox.sandbox_service import (
    SandboxResult,
)


@dataclass
class TestExecutionResult:
    """
    Structured result of repository test execution.
    """

    command: list[str]
    exit_code: int
    stdout: str
    stderr: str
    passed: bool
    timed_out: bool


class RepositoryTestExecutionService:
    """
    Coordinates repository test execution through the
    configured sandbox.
    """

    def __init__(
        self,
        sandbox_service: DockerSandbox | None = None,
    ):
        self.sandbox_service = (
            sandbox_service
            if sandbox_service is not None
            else DockerSandbox()
        )

    def build_test_command(
        self,
        test_target: str | None = None,
    ) -> list[str]:
        command = [
            "python",
            "-m",
            "pytest",
        ]

        if test_target:
            command.append(test_target)

        return command

    def execute_tests(
        self,
        workspace_path: str,
        test_target: str | None = None,
    ) -> TestExecutionResult:
        command = self.build_test_command(
            test_target=test_target,
        )

        result: SandboxResult = (
            self.sandbox_service.execute(
                command=command,
                workspace_path=workspace_path,
            )
        )

        return TestExecutionResult(
            command=command,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            passed=(
                result.exit_code == 0
                and not result.timed_out
            ),
            timed_out=result.timed_out,
        )
