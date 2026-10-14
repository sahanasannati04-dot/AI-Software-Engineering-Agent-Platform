from unittest.mock import Mock, patch

from app.services.tools.bug_analysis_tool import (
    prepare_bug_analysis,
)


@patch(
    "app.services.tools.bug_analysis_tool.search_code"
)
def test_prepare_bug_analysis_returns_relevant_context(
    mock_search_code,
):
    db = Mock()

    mock_search_code.return_value = [
        {
            "path": "hotel/views.py",
            "start_line": 100,
            "end_line": 115,
            "symbol_name": "room_has_booking_conflict",
            "relevance_score": 0.92,
            "content": (
                "def room_has_booking_conflict():\n"
                "    return True"
            ),
        }
    ]

    result = prepare_bug_analysis(
        db=db,
        repository_id=1,
        bug_description="Room booking conflict occurs.",
    )

    assert result["repository_id"] == 1
    assert result["bug_description"] == (
        "Room booking conflict occurs."
    )

    assert len(result["matches"]) == 1

    assert result["matches"][0]["path"] == (
        "hotel/views.py"
    )

    assert "Possible Relevant Code 1" in result["context"]
    assert "hotel/views.py:100-115" in result["context"]
    assert "room_has_booking_conflict" in result["context"]
    assert "0.9200" in result["context"]

    mock_search_code.assert_called_once_with(
        db=db,
        repository_id=1,
        query="Room booking conflict occurs.",
        limit=5,
    )


@patch(
    "app.services.tools.bug_analysis_tool.search_code"
)
def test_prepare_bug_analysis_supports_custom_limit(
    mock_search_code,
):
    db = Mock()

    mock_search_code.return_value = []

    result = prepare_bug_analysis(
        db=db,
        repository_id=7,
        bug_description="Database connection failure.",
        limit=10,
    )

    assert result["repository_id"] == 7
    assert result["matches"] == []
    assert result["context"] == ""

    mock_search_code.assert_called_once_with(
        db=db,
        repository_id=7,
        query="Database connection failure.",
        limit=10,
    )


@patch(
    "app.services.tools.bug_analysis_tool.search_code"
)
def test_prepare_bug_analysis_handles_empty_description(
    mock_search_code,
):
    db = Mock()

    result = prepare_bug_analysis(
        db=db,
        repository_id=1,
        bug_description="",
    )

    assert result == {
        "repository_id": 1,
        "bug_description": "",
        "matches": [],
        "context": "",
    }

    mock_search_code.assert_not_called()


@patch(
    "app.services.tools.bug_analysis_tool.search_code"
)
def test_prepare_bug_analysis_handles_multiple_matches(
    mock_search_code,
):
    db = Mock()

    mock_search_code.return_value = [
        {
            "path": "hotel/views.py",
            "start_line": 10,
            "end_line": 20,
            "symbol_name": "create_booking",
            "relevance_score": 0.90,
            "content": "def create_booking(): pass",
        },
        {
            "path": "hotel/models.py",
            "start_line": 30,
            "end_line": 40,
            "symbol_name": "Booking",
            "relevance_score": 0.82,
            "content": "class Booking: pass",
        },
    ]

    result = prepare_bug_analysis(
        db=db,
        repository_id=1,
        bug_description="Booking creation fails.",
    )

    assert len(result["matches"]) == 2

    assert "Possible Relevant Code 1" in result["context"]
    assert "Possible Relevant Code 2" in result["context"]

    assert "hotel/views.py:10-20" in result["context"]
    assert "hotel/models.py:30-40" in result["context"]

    assert "create_booking" in result["context"]
    assert "Booking" in result["context"]


@patch(
    "app.services.tools.bug_analysis_tool.search_code"
)
def test_prepare_bug_analysis_handles_single_line_match(
    mock_search_code,
):
    db = Mock()

    mock_search_code.return_value = [
        {
            "path": "app/service.py",
            "start_line": 25,
            "end_line": None,
            "symbol_name": "process_request",
            "relevance_score": 0.75,
            "content": "def process_request(): pass",
        }
    ]

    result = prepare_bug_analysis(
        db=db,
        repository_id=1,
        bug_description="Request processing bug.",
    )

    assert "app/service.py:25" in result["context"]
    assert "process_request" in result["context"]
    assert "0.7500" in result["context"]