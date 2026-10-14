from unittest.mock import Mock, patch

import pytest

from app.services.tools.executor import (
    ToolExecutionError,
    execute_tool,
)


def test_execute_tool_rejects_empty_tool_name():
    with pytest.raises(
        ToolExecutionError,
        match="Tool name cannot be empty.",
    ):
        execute_tool(
            tool_name="",
            arguments={},
        )


def test_execute_tool_rejects_invalid_arguments():
    with pytest.raises(
        ToolExecutionError,
        match="Tool arguments must be a dictionary.",
    ):
        execute_tool(
            tool_name="test_tool",
            arguments="invalid",
        )


def test_execute_tool_rejects_unknown_tool():
    with pytest.raises(
        ToolExecutionError,
        match="Tool 'unknown_tool' is not registered.",
    ):
        execute_tool(
            tool_name="unknown_tool",
            arguments={},
        )


def test_execute_tool_calls_registered_tool():
    mock_tool = Mock(
        return_value={
            "status": "success",
        }
    )

    with patch(
        "app.services.tools.executor.get_tool",
        return_value=mock_tool,
    ):
        result = execute_tool(
            tool_name="test_tool",
            arguments={
                "repository_id": 1,
                "query": "authentication",
            },
        )

    assert result == {
        "status": "success",
    }

    mock_tool.assert_called_once_with(
        repository_id=1,
        query="authentication",
    )


def test_execute_tool_converts_tool_exception():
    mock_tool = Mock(
        side_effect=RuntimeError(
            "Something went wrong."
        )
    )

    with patch(
        "app.services.tools.executor.get_tool",
        return_value=mock_tool,
    ):
        with pytest.raises(
            ToolExecutionError,
            match="Tool 'test_tool' execution failed",
        ):
            execute_tool(
                tool_name="test_tool",
                arguments={},
            )


def test_execute_tool_allows_empty_arguments():
    mock_tool = Mock(
        return_value={
            "status": "success",
        }
    )

    with patch(
        "app.services.tools.executor.get_tool",
        return_value=mock_tool,
    ):
        result = execute_tool(
            tool_name="test_tool",
            arguments={},
        )

    assert result == {
        "status": "success",
    }

    mock_tool.assert_called_once_with()