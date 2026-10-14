from types import SimpleNamespace
from unittest.mock import patch

from app.services.agent_response_service import (
    answer_with_tools,
)


def test_direct_answer_uses_user_request():
    fake_provider = SimpleNamespace(
        generate=lambda prompt, system_prompt=None: (
            "Python is a high-level programming language."
        )
    )

    fake_tool_result = {
        "action": "direct_answer",
    }

    with patch(
        "app.services.agent_response_service.run_agent_tool",
        return_value=fake_tool_result,
    ) as mock_agent, patch(
        "app.services.agent_response_service.GeminiProvider",
        return_value=fake_provider,
    ):
        result = answer_with_tools(
            db=None,
            repository_id=1,
            user_request="What is Python?",
        )

    assert result["action"] == "direct_answer"

    assert result["answer"] == (
        "Python is a high-level programming language."
    )

    assert result["tool_name"] is None
    assert result["tool_result"] is None
    assert result["steps"] == []

    mock_agent.assert_called_once_with(
        db=None,
        repository_id=1,
        user_request="What is Python?",
        conversation_context="",
    )


def test_direct_answer_includes_conversation_context():
    captured = {}

    def fake_generate(prompt, system_prompt=None):
        captured["prompt"] = prompt
        captured["system_prompt"] = system_prompt

        return "The function is located in hotel/views.py."

    fake_provider = SimpleNamespace(
        generate=fake_generate
    )

    with patch(
        "app.services.agent_response_service.run_agent_tool",
        return_value={
            "action": "direct_answer",
        },
    ), patch(
        "app.services.agent_response_service.GeminiProvider",
        return_value=fake_provider,
    ):
        result = answer_with_tools(
            db=None,
            repository_id=1,
            user_request="Where is that function?",
            conversation_context=(
                "USER: Find the booking conflict function.\n"
                "ASSISTANT: It is in hotel/views.py."
            ),
        )

    assert result["answer"] == (
        "The function is located in hotel/views.py."
    )

    assert (
        "Conversation history:"
        in captured["prompt"]
    )

    assert (
        "Find the booking conflict function."
        in captured["prompt"]
    )

    assert (
        "Current user request:"
        in captured["prompt"]
    )

    assert (
        "Where is that function?"
        in captured["prompt"]
    )

    assert captured["system_prompt"] is not None
    assert "final response component" in (
        captured["system_prompt"]
    )


def test_tool_assisted_answer_uses_execution_history():
    captured = {}

    execution_history = [
        {
            "step": 1,
            "tool_name": "inspect_repository",
            "arguments": {},
            "result": {
                "name": "Luxury Grand Hotel",
            },
        },
        {
            "step": 2,
            "tool_name": "inspect_symbol",
            "arguments": {
                "symbol_name": "room_has_booking_conflict",
            },
            "result": {
                "path": "hotel/views.py",
                "start_line": 172,
                "end_line": 200,
            },
        },
    ]

    fake_tool_result = {
        "action": "tool_call",
        "tool_name": "inspect_symbol",
        "arguments": {
            "symbol_name": "room_has_booking_conflict",
        },
        "result": {
            "path": "hotel/views.py",
            "start_line": 172,
            "end_line": 200,
        },
        "steps": execution_history,
    }

    def fake_generate(prompt, system_prompt=None):
        captured["prompt"] = prompt
        captured["system_prompt"] = system_prompt

        return (
            "The function is implemented in "
            "hotel/views.py at lines 172-200."
        )

    fake_provider = SimpleNamespace(
        generate=fake_generate
    )

    with patch(
        "app.services.agent_response_service.run_agent_tool",
        return_value=fake_tool_result,
    ), patch(
        "app.services.agent_response_service.GeminiProvider",
        return_value=fake_provider,
    ):
        result = answer_with_tools(
            db=None,
            repository_id=1,
            user_request=(
                "Where is room_has_booking_conflict "
                "implemented?"
            ),
        )

    assert result["action"] == "tool_call"

    assert result["answer"] == (
        "The function is implemented in "
        "hotel/views.py at lines 172-200."
    )

    assert result["tool_name"] == "inspect_symbol"

    assert result["tool_result"] == {
        "path": "hotel/views.py",
        "start_line": 172,
        "end_line": 200,
    }

    assert result["steps"] == execution_history

    assert "Repository investigation history:" in (
        captured["prompt"]
    )

    assert "inspect_repository" in captured["prompt"]
    assert "inspect_symbol" in captured["prompt"]
    assert "room_has_booking_conflict" in (
        captured["prompt"]
    )

    assert captured["system_prompt"] is not None


def test_tool_assisted_answer_includes_conversation_context():
    captured = {}

    def fake_generate(prompt, system_prompt=None):
        captured["prompt"] = prompt

        return "The conflict check is in hotel/views.py."

    fake_provider = SimpleNamespace(
        generate=fake_generate
    )

    fake_tool_result = {
        "action": "tool_call",
        "tool_name": "inspect_symbol",
        "result": {
            "path": "hotel/views.py",
        },
        "steps": [
            {
                "step": 1,
                "tool_name": "inspect_symbol",
                "arguments": {
                    "symbol_name": "room_has_booking_conflict",
                },
                "result": {
                    "path": "hotel/views.py",
                },
            }
        ],
    }

    with patch(
        "app.services.agent_response_service.run_agent_tool",
        return_value=fake_tool_result,
    ), patch(
        "app.services.agent_response_service.GeminiProvider",
        return_value=fake_provider,
    ):
        result = answer_with_tools(
            db=None,
            repository_id=1,
            user_request="Explain that function.",
            conversation_context=(
                "USER: Find the booking conflict function.\n"
                "ASSISTANT: It is in hotel/views.py."
            ),
        )

    assert result["answer"] == (
        "The conflict check is in hotel/views.py."
    )

    assert "Conversation history:" in (
        captured["prompt"]
    )

    assert "Find the booking conflict function." in (
        captured["prompt"]
    )

    assert "Explain that function." in (
        captured["prompt"]
    )

    assert "room_has_booking_conflict" in (
        captured["prompt"]
    )