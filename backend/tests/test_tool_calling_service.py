from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.services.tool_calling_service import (
    select_tool,
)


def test_empty_request_returns_direct_answer():
    result = select_tool("")

    assert result == {
        "action": "direct_answer",
    }


def test_valid_tool_call_is_parsed():
    fake_provider = SimpleNamespace(
        generate=lambda prompt, system_prompt=None: (
            '{"action": "tool_call", '
            '"tool_name": "inspect_symbol", '
            '"arguments": {"symbol_name": '
            '"room_has_booking_conflict"}}'
        )
    )

    with patch(
        "app.services.tool_calling_service.GeminiProvider",
        return_value=fake_provider,
    ):
        result = select_tool(
            "Find the room_has_booking_conflict function."
        )

    assert result["action"] == "tool_call"
    assert result["tool_name"] == "inspect_symbol"
    assert result["arguments"] == {
        "symbol_name": "room_has_booking_conflict",
    }


def test_valid_direct_answer_is_parsed():
    fake_provider = SimpleNamespace(
        generate=lambda prompt, system_prompt=None: (
            '{"action": "direct_answer"}'
        )
    )

    with patch(
        "app.services.tool_calling_service.GeminiProvider",
        return_value=fake_provider,
    ):
        result = select_tool(
            "What is Python?"
        )

    assert result == {
        "action": "direct_answer",
    }


def test_invalid_json_raises_error():
    fake_provider = SimpleNamespace(
        generate=lambda prompt, system_prompt=None: (
            "not valid json"
        )
    )

    with patch(
        "app.services.tool_calling_service.GeminiProvider",
        return_value=fake_provider,
    ):
        with pytest.raises(
            RuntimeError,
            match="invalid tool-selection JSON",
        ):
            select_tool(
                "Inspect the repository."
            )


def test_invalid_action_raises_error():
    fake_provider = SimpleNamespace(
        generate=lambda prompt, system_prompt=None: (
            '{"action": "invalid_action"}'
        )
    )

    with patch(
        "app.services.tool_calling_service.GeminiProvider",
        return_value=fake_provider,
    ):
        with pytest.raises(
            RuntimeError,
            match="invalid tool-selection action",
        ):
            select_tool(
                "Inspect the repository."
            )


def test_unknown_tool_raises_error():
    fake_provider = SimpleNamespace(
        generate=lambda prompt, system_prompt=None: (
            '{"action": "tool_call", '
            '"tool_name": "fake_unknown_tool", '
            '"arguments": {}}'
        )
    )

    with patch(
        "app.services.tool_calling_service.GeminiProvider",
        return_value=fake_provider,
    ):
        with pytest.raises(
            RuntimeError,
            match="unknown tool",
        ):
            select_tool(
                "Inspect the repository."
            )


def test_missing_tool_name_raises_error():
    fake_provider = SimpleNamespace(
        generate=lambda prompt, system_prompt=None: (
            '{"action": "tool_call", '
            '"arguments": {}}'
        )
    )

    with patch(
        "app.services.tool_calling_service.GeminiProvider",
        return_value=fake_provider,
    ):
        with pytest.raises(
            RuntimeError,
            match="did not provide a tool name",
        ):
            select_tool(
                "Inspect the repository."
            )


def test_invalid_tool_arguments_raise_error():
    fake_provider = SimpleNamespace(
        generate=lambda prompt, system_prompt=None: (
            '{"action": "tool_call", '
            '"tool_name": "inspect_symbol", '
            '"arguments": "invalid"}'
        )
    )

    with patch(
        "app.services.tool_calling_service.GeminiProvider",
        return_value=fake_provider,
    ):
        with pytest.raises(
            RuntimeError,
            match="invalid tool arguments",
        ):
            select_tool(
                "Inspect the repository."
            )


def test_conversation_context_is_passed_to_provider():
    captured = {}

    def fake_generate(
        prompt,
        system_prompt=None,
    ):
        captured["prompt"] = prompt
        captured["system_prompt"] = system_prompt

        return (
            '{"action": "tool_call", '
            '"tool_name": "inspect_symbol", '
            '"arguments": {"symbol_name": '
            '"room_has_booking_conflict"}}'
        )

    fake_provider = SimpleNamespace(
        generate=fake_generate
    )

    with patch(
        "app.services.tool_calling_service.GeminiProvider",
        return_value=fake_provider,
    ):
        result = select_tool(
            user_request="Explain that function.",
            conversation_context=(
                "USER: Find the booking conflict function.\n"
                "ASSISTANT: It is in hotel/views.py."
            ),
        )

    assert result["action"] == "tool_call"
    assert result["tool_name"] == "inspect_symbol"

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
        "Explain that function."
        in captured["prompt"]
    )

    assert captured["system_prompt"] is not None

    # The Gemini-facing schema uses the canonical schema name.
    assert "symbol_inspection" in captured["system_prompt"]

    # The executable registry name is not required in the
    # Gemini-facing prompt.
    assert '"name": "symbol_inspection"' in (
        captured["system_prompt"]
    )