import pytest

from app.services.sandbox.sandbox_service import (
    SandboxConfigurationError,
    SandboxExecutionError,
    SandboxService,
)


def test_sandbox_rejects_empty_command():
    sandbox = SandboxService()

    with pytest.raises(
        SandboxExecutionError,
        match="Sandbox command cannot be empty.",
    ):
        sandbox.execute(
            command=[],
            workspace_path="workspace/test",
        )


def test_sandbox_rejects_empty_workspace():
    sandbox = SandboxService()

    with pytest.raises(
        SandboxExecutionError,
        match="Workspace path cannot be empty.",
    ):
        sandbox.execute(
            command=["python", "--version"],
            workspace_path="",
        )


def test_sandbox_requires_docker_runtime():
    sandbox = SandboxService()

    with pytest.raises(
        SandboxConfigurationError,
        match="Docker sandbox runtime is not available.",
    ):
        sandbox.execute(
            command=["python", "--version"],
            workspace_path="workspace/test",
        )


def test_sandbox_rejects_invalid_timeout():
    with pytest.raises(
        SandboxConfigurationError,
        match="timeout_seconds must be greater than zero.",
    ):
        SandboxService(timeout_seconds=0)


def test_sandbox_rejects_invalid_cpu_limit():
    with pytest.raises(
        SandboxConfigurationError,
        match="cpu_limit must be greater than zero.",
    ):
        SandboxService(cpu_limit=0)


def test_sandbox_rejects_empty_memory_limit():
    with pytest.raises(
        SandboxConfigurationError,
        match="memory_limit cannot be empty.",
    ):
        SandboxService(memory_limit="")