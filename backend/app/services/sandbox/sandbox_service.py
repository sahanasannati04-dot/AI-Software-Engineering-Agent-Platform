from dataclasses import dataclass


class SandboxError(Exception):
    """Base exception for sandbox execution errors."""


class SandboxConfigurationError(SandboxError):
    """Raised when the sandbox is incorrectly configured."""


class SandboxExecutionError(SandboxError):
    """Raised when sandbox execution fails."""


@dataclass
class SandboxResult:
    """
    Result returned from a sandbox execution.
    """

    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


class SandboxService:
    """
    Abstraction for executing repository commands inside
    an isolated sandbox.

    Docker-backed execution will be connected later.
    """

    def __init__(
        self,
        timeout_seconds: int = 30,
        memory_limit: str = "512m",
        cpu_limit: float = 1.0,
    ):
        if timeout_seconds <= 0:
            raise SandboxConfigurationError(
                "timeout_seconds must be greater than zero."
            )

        if cpu_limit <= 0:
            raise SandboxConfigurationError(
                "cpu_limit must be greater than zero."
            )

        if not memory_limit.strip():
            raise SandboxConfigurationError(
                "memory_limit cannot be empty."
            )

        self.timeout_seconds = timeout_seconds
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit

    def execute(
        self,
        command: list[str],
        workspace_path: str,
    ) -> SandboxResult:
        """
        Execute a command inside the sandbox.

        Docker execution is intentionally not enabled until
        the Docker runtime is available.
        """

        if not command:
            raise SandboxExecutionError(
                "Sandbox command cannot be empty."
            )

        if not workspace_path.strip():
            raise SandboxExecutionError(
                "Workspace path cannot be empty."
            )

        raise SandboxConfigurationError(
            "Docker sandbox runtime is not available. "
            "Install and start Docker Desktop before "
            "executing sandbox commands."
        )