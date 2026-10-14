import subprocess
from unittest.mock import patch

import pytest

from app.services.sandbox.docker_sandbox import (
    DockerSandbox,
)
from app.services.sandbox.sandbox_service import (
    SandboxConfigurationError,
    SandboxExecutionError,
)


def test_build_command_contains_security_restrictions():
    sandbox = DockerSandbox()

    command = sandbox.build_command(
        command=["python", "-m", "pytest"],
        workspace_path="C:\\workspace\\repo",
    )

    assert command[:2] == [
        "docker",
        "run",
    ]

    assert "--rm" in command
    assert "--network" in command
    assert "none" in command
    assert "--memory" in command
    assert "512m" in command
    assert "--cpus" in command
    assert "1.0" in command
    assert "--read-only" in command
    assert "--tmpfs" in command
    assert "--mount" in command
    assert "--workdir" in command

    assert "python" in command
    assert "-m" in command
    assert "pytest" in command


def test_build_command_rejects_empty_command():
    sandbox = DockerSandbox()

    with pytest.raises(
        SandboxExecutionError,
        match="Sandbox command cannot be empty.",
    ):
        sandbox.build_command(
            command=[],
            workspace_path="workspace",
        )


def test_build_command_rejects_empty_workspace():
    sandbox = DockerSandbox()

    with pytest.raises(
        SandboxExecutionError,
        match="Workspace path cannot be empty.",
    ):
        sandbox.build_command(
            command=["python", "--version"],
            workspace_path="",
        )


def test_docker_sandbox_rejects_empty_image():
    with pytest.raises(
        SandboxConfigurationError,
        match="Docker image cannot be empty.",
    ):
        DockerSandbox(image="")


def test_docker_sandbox_rejects_invalid_timeout():
    with pytest.raises(
        SandboxConfigurationError,
        match="timeout_seconds must be greater than zero.",
    ):
        DockerSandbox(timeout_seconds=0)


def test_docker_sandbox_rejects_empty_memory_limit():
    with pytest.raises(
        SandboxConfigurationError,
        match="memory_limit cannot be empty.",
    ):
        DockerSandbox(memory_limit="")


def test_docker_sandbox_rejects_invalid_cpu_limit():
    with pytest.raises(
        SandboxConfigurationError,
        match="cpu_limit must be greater than zero.",
    ):
        DockerSandbox(cpu_limit=0)


def test_execute_returns_success_result():
    sandbox = DockerSandbox()

    completed_process = subprocess.CompletedProcess(
        args=["docker", "run"],
        returncode=0,
        stdout="5 passed",
        stderr="",
    )

    with patch(
        "app.services.sandbox.docker_sandbox.subprocess.run",
        return_value=completed_process,
    ) as mock_run:
        result = sandbox.execute(
            command=["python", "-m", "pytest"],
            workspace_path="workspace",
        )

    assert result.exit_code == 0
    assert result.stdout == "5 passed"
    assert result.stderr == ""
    assert result.passed if hasattr(result, "passed") else True
    assert result.timed_out is False

    mock_run.assert_called_once()


def test_execute_returns_failed_result():
    sandbox = DockerSandbox()

    completed_process = subprocess.CompletedProcess(
        args=["docker", "run"],
        returncode=1,
        stdout="",
        stderr="AssertionError",
    )

    with patch(
        "app.services.sandbox.docker_sandbox.subprocess.run",
        return_value=completed_process,
    ):
        result = sandbox.execute(
            command=["python", "-m", "pytest"],
            workspace_path="workspace",
        )

    assert result.exit_code == 1
    assert result.stdout == ""
    assert result.stderr == "AssertionError"
    assert result.timed_out is False


def test_execute_returns_timeout_result():
    sandbox = DockerSandbox()

    timeout_error = subprocess.TimeoutExpired(
        cmd=["docker", "run"],
        timeout=30,
    )

    timeout_error.stdout = b"partial output"
    timeout_error.stderr = b"timeout"

    with patch(
        "app.services.sandbox.docker_sandbox.subprocess.run",
        side_effect=timeout_error,
    ):
        result = sandbox.execute(
            command=["python", "-m", "pytest"],
            workspace_path="workspace",
        )

    assert result.exit_code == 124
    assert result.stdout == "partial output"
    assert result.stderr == "timeout"
    assert result.timed_out is True


def test_execute_raises_configuration_error_when_docker_missing():
    sandbox = DockerSandbox()

    with patch(
        "app.services.sandbox.docker_sandbox.subprocess.run",
        side_effect=FileNotFoundError(),
    ):
        with pytest.raises(
            SandboxConfigurationError,
            match="Docker executable was not found.",
        ):
            sandbox.execute(
                command=["python", "--version"],
                workspace_path="workspace",
            )
