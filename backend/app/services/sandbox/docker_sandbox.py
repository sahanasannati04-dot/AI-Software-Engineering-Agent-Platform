import subprocess

from app.services.sandbox.sandbox_service import (
    SandboxConfigurationError,
    SandboxExecutionError,
    SandboxResult,
)


class DockerSandbox:
    """
    Docker-backed sandbox execution adapter.

    The adapter is intentionally isolated from the rest of the
    application so the sandbox implementation can be replaced
    without changing agent or execution services.
    """

    def __init__(
        self,
        image: str = "python:3.13-slim",
        timeout_seconds: int = 30,
        memory_limit: str = "512m",
        cpu_limit: float = 1.0,
    ):
        if not image.strip():
            raise SandboxConfigurationError(
                "Docker image cannot be empty."
            )

        if timeout_seconds <= 0:
            raise SandboxConfigurationError(
                "timeout_seconds must be greater than zero."
            )

        if not memory_limit.strip():
            raise SandboxConfigurationError(
                "memory_limit cannot be empty."
            )

        if cpu_limit <= 0:
            raise SandboxConfigurationError(
                "cpu_limit must be greater than zero."
            )

        self.image = image
        self.timeout_seconds = timeout_seconds
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit

    def build_command(
        self,
        command: list[str],
        workspace_path: str,
    ) -> list[str]:
        if not command:
            raise SandboxExecutionError(
                "Sandbox command cannot be empty."
            )

        if not workspace_path.strip():
            raise SandboxExecutionError(
                "Workspace path cannot be empty."
            )

        return [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--memory",
            self.memory_limit,
            "--cpus",
            str(self.cpu_limit),
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            "--mount",
            f"type=bind,source={workspace_path},target=/workspace,readonly",
            "--workdir",
            "/workspace",
            self.image,
            *command,
        ]

    def execute(
        self,
        command: list[str],
        workspace_path: str,
    ) -> SandboxResult:
        docker_command = self.build_command(
            command=command,
            workspace_path=workspace_path,
        )

        try:
            result = subprocess.run(
                docker_command,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )

        except FileNotFoundError as exc:
            raise SandboxConfigurationError(
                "Docker executable was not found. "
                "Install Docker Desktop and ensure Docker "
                "is available on PATH."
            ) from exc

        except subprocess.TimeoutExpired as exc:
            return SandboxResult(
                exit_code=124,
                stdout=(
                    exc.stdout.decode(errors="replace")
                    if isinstance(exc.stdout, bytes)
                    else (exc.stdout or "")
                ),
                stderr=(
                    exc.stderr.decode(errors="replace")
                    if isinstance(exc.stderr, bytes)
                    else (exc.stderr or "")
                ),
                timed_out=True,
            )

        if result.returncode != 0:
            return SandboxResult(
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                timed_out=False,
            )

        return SandboxResult(
            exit_code=0,
            stdout=result.stdout,
            stderr=result.stderr,
            timed_out=False,
        )
