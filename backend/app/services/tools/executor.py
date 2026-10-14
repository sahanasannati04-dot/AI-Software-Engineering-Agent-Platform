from typing import Any

from app.services.tools.registry import get_tool


class ToolExecutionError(Exception):
    """
    Raised when a registered tool cannot be executed.
    """


def execute_tool(
    tool_name: str,
    arguments: dict[str, Any],
) -> Any:
    """
    Execute a registered engineering tool.

    The executor provides a single controlled entry point
    for the AI agent to invoke repository engineering tools.
    """

    if not tool_name.strip():
        raise ToolExecutionError(
            "Tool name cannot be empty."
        )

    if arguments is None:
        arguments = {}

    if not isinstance(arguments, dict):
        raise ToolExecutionError(
            "Tool arguments must be a dictionary."
        )

    tool = get_tool(tool_name)

    if tool is None:
        raise ToolExecutionError(
            f"Tool '{tool_name}' is not registered."
        )

    try:
        return tool(**arguments)

    except ToolExecutionError:
        raise

    except Exception as exc:
        raise ToolExecutionError(
            f"Tool '{tool_name}' execution failed: {exc}"
        ) from exc