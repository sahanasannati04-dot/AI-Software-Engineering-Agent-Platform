from types import SimpleNamespace
from unittest.mock import patch

from app.services.repository_intelligence.rag_service import (
    answer_repository_question,
)


class FakeChunk:
    def __init__(
        self,
        path,
        symbol_name,
        start_line,
        end_line,
        chunk_type="function",
        relevance_score=0.9,
    ):
        self.path = path
        self.symbol_name = symbol_name
        self.start_line = start_line
        self.end_line = end_line
        self.chunk_type = chunk_type
        self.relevance_score = relevance_score
        self.distance = 0.1
        self.content = (
            "def room_has_booking_conflict("
            "room, check_in, check_out):\n"
            "    return True"
        )


class FakeRAGContext:
    def __init__(self):
        self.chunks = [
            FakeChunk(
                path="hotel/views.py",
                symbol_name="room_has_booking_conflict",
                start_line=172,
                end_line=200,
            )
        ]

        self.context_text = (
            "File: hotel/views.py:172-200\n"
            "Symbol: room_has_booking_conflict\n"
            "The function checks whether a room has "
            "an overlapping booking."
        )


def test_answer_repository_question_returns_llm_answer():
    fake_context = FakeRAGContext()

    fake_intent = SimpleNamespace(
        intent=SimpleNamespace(value="code_explanation"),
        confidence=0.95,
    )

    fake_provider = SimpleNamespace(
        generate=lambda prompt, system_prompt=None: (
            "The booking conflict check looks for "
            "overlapping reservations."
        )
    )

    with patch(
        "app.services.repository_intelligence.rag_service.classify_intent",
        return_value=fake_intent,
    ), patch(
        "app.services.repository_intelligence.rag_service.build_rag_context",
        return_value=fake_context,
    ), patch(
        "app.services.repository_intelligence.rag_service.GeminiProvider",
        return_value=fake_provider,
    ):
        result = answer_repository_question(
            db=None,
            repository_id=1,
            question=(
                "How does the booking conflict check "
                "prevent overlapping reservations?"
            ),
            limit=3,
        )

    assert result["answer"] == (
        "The booking conflict check looks for "
        "overlapping reservations."
    )

    assert result["intent"] == "code_explanation"
    assert result["intent_confidence"] == 0.95

    assert len(result["sources"]) == 1

    source = result["sources"][0]

    assert source["path"] == "hotel/views.py"
    assert source["symbol_name"] == "room_has_booking_conflict"
    assert source["start_line"] == 172
    assert source["end_line"] == 200


def test_answer_repository_question_returns_empty_context_message():
    fake_context = SimpleNamespace(
        chunks=[],
        context_text="",
    )

    fake_intent = SimpleNamespace(
        intent=SimpleNamespace(value="general_question"),
        confidence=0.90,
    )

    with patch(
        "app.services.repository_intelligence.rag_service.classify_intent",
        return_value=fake_intent,
    ), patch(
        "app.services.repository_intelligence.rag_service.build_rag_context",
        return_value=fake_context,
    ):
        result = answer_repository_question(
            db=None,
            repository_id=1,
            question="Explain the booking system.",
            limit=3,
        )

    assert result["answer"] == (
        "I could not find relevant code in this repository "
        "to answer the question."
    )

    assert result["sources"] == []
    assert result["intent"] == "general_question"
    assert result["intent_confidence"] == 0.90