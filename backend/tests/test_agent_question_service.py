from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.services.agent_question_service import (
    answer_agent_question,
)


def test_empty_question_returns_validation_response():
    result = answer_agent_question(
        db=None,
        repository_id=1,
        question="",
    )

    assert result == {
        "answer": "Please provide a repository question.",
        "intent": "general_question",
        "intent_confidence": 1.0,
        "steps": [],
    }


def test_agent_question_without_conversation():
    fake_intent = SimpleNamespace(
        intent=SimpleNamespace(value="code_search"),
        confidence=0.94,
    )

    fake_agent_result = {
        "answer": (
            "The booking conflict logic is implemented "
            "in hotel/views.py."
        ),
        "steps": [
            {
                "step": 1,
                "tool_name": "search_code",
                "arguments": {
                    "query": "booking conflict",
                },
                "result": {
                    "found": True,
                },
            }
        ],
    }

    with patch(
        "app.services.agent_question_service.classify_intent",
        return_value=fake_intent,
    ), patch(
        "app.services.agent_question_service.answer_with_tools",
        return_value=fake_agent_result,
    ) as mock_agent:
        result = answer_agent_question(
            db=None,
            repository_id=1,
            question="Find the booking conflict logic.",
        )

    assert result["answer"] == (
        "The booking conflict logic is implemented "
        "in hotel/views.py."
    )

    assert result["intent"] == "code_search"
    assert result["intent_confidence"] == 0.94

    assert len(result["steps"]) == 1
    assert result["steps"][0]["tool_name"] == "search_code"

    mock_agent.assert_called_once_with(
        db=None,
        repository_id=1,
        user_request="Find the booking conflict logic.",
        conversation_context="",
    )


def test_conversation_context_is_used_and_messages_are_saved():
    fake_intent = SimpleNamespace(
        intent=SimpleNamespace(value="code_explanation"),
        confidence=0.91,
    )

    fake_conversation = SimpleNamespace(
        id=7,
        repository_id=1,
    )

    fake_agent_result = {
        "answer": "The function checks for overlapping bookings.",
        "steps": [
            {
                "step": 1,
                "tool_name": "inspect_symbol",
                "arguments": {
                    "symbol_name": "room_has_booking_conflict",
                },
                "result": {
                    "found": True,
                },
            }
        ],
    }

    with patch(
        "app.services.agent_question_service.classify_intent",
        return_value=fake_intent,
    ), patch(
        "app.services.agent_question_service.get_conversation",
        return_value=fake_conversation,
    ), patch(
        "app.services.agent_question_service.build_conversation_context",
        return_value=(
            "USER: Find the booking conflict function.\n"
            "ASSISTANT: It is in hotel/views.py."
        ),
    ) as mock_context, patch(
        "app.services.agent_question_service.answer_with_tools",
        return_value=fake_agent_result,
    ) as mock_agent, patch(
        "app.services.agent_question_service.add_message",
    ) as mock_add_message:
        result = answer_agent_question(
            db=None,
            repository_id=1,
            question="Explain that function.",
            conversation_id=7,
            user_id=1,
        )

    assert result["answer"] == (
        "The function checks for overlapping bookings."
    )

    assert result["intent"] == "code_explanation"
    assert result["intent_confidence"] == 0.91

    mock_context.assert_called_once_with(
        db=None,
        conversation_id=7,
        user_id=1,
        max_messages=10,
    )

    mock_agent.assert_called_once_with(
        db=None,
        repository_id=1,
        user_request="Explain that function.",
        conversation_context=(
            "USER: Find the booking conflict function.\n"
            "ASSISTANT: It is in hotel/views.py."
        ),
    )

    assert mock_add_message.call_count == 2

    mock_add_message.assert_any_call(
        db=None,
        conversation_id=7,
        role="user",
        content="Explain that function.",
    )

    mock_add_message.assert_any_call(
        db=None,
        conversation_id=7,
        role="assistant",
        content=(
            "The function checks for overlapping bookings."
        ),
    )


def test_conversation_requires_user_id():
    fake_intent = SimpleNamespace(
        intent=SimpleNamespace(value="general_question"),
        confidence=0.90,
    )

    with patch(
        "app.services.agent_question_service.classify_intent",
        return_value=fake_intent,
    ):
        with pytest.raises(
            ValueError,
            match="user_id is required",
        ):
            answer_agent_question(
                db=None,
                repository_id=1,
                question="Explain the booking system.",
                conversation_id=7,
                user_id=None,
            )


def test_missing_conversation_raises_error():
    fake_intent = SimpleNamespace(
        intent=SimpleNamespace(value="general_question"),
        confidence=0.90,
    )

    with patch(
        "app.services.agent_question_service.classify_intent",
        return_value=fake_intent,
    ), patch(
        "app.services.agent_question_service.get_conversation",
        return_value=None,
    ):
        with pytest.raises(
            ValueError,
            match="Conversation not found",
        ):
            answer_agent_question(
                db=None,
                repository_id=1,
                question="Explain the booking system.",
                conversation_id=7,
                user_id=1,
            )


def test_conversation_repository_mismatch_raises_error():
    fake_intent = SimpleNamespace(
        intent=SimpleNamespace(value="general_question"),
        confidence=0.90,
    )

    fake_conversation = SimpleNamespace(
        id=7,
        repository_id=999,
    )

    with patch(
        "app.services.agent_question_service.classify_intent",
        return_value=fake_intent,
    ), patch(
        "app.services.agent_question_service.get_conversation",
        return_value=fake_conversation,
    ):
        with pytest.raises(
            ValueError,
            match="does not belong to this repository",
        ):
            answer_agent_question(
                db=None,
                repository_id=1,
                question="Explain the booking system.",
                conversation_id=7,
                user_id=1,
            )


def test_missing_steps_are_returned_as_empty_list():
    fake_intent = SimpleNamespace(
        intent=SimpleNamespace(value="general_question"),
        confidence=0.88,
    )

    fake_agent_result = {
        "answer": "This is a direct answer.",
    }

    with patch(
        "app.services.agent_question_service.classify_intent",
        return_value=fake_intent,
    ), patch(
        "app.services.agent_question_service.answer_with_tools",
        return_value=fake_agent_result,
    ):
        result = answer_agent_question(
            db=None,
            repository_id=1,
            question="What is Python?",
        )

    assert result["answer"] == "This is a direct answer."
    assert result["intent"] == "general_question"
    assert result["intent_confidence"] == 0.88
    assert result["steps"] == []