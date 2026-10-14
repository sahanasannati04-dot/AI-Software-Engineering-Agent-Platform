from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.tools.code_modification_tool import (
    prepare_code_modification,
)


def test_empty_modification_request_returns_empty_context():
    result = prepare_code_modification(
        db=None,
        repository_id=1,
        modification_request="",
    )

    assert result == {
        "repository_id": 1,
        "modification_request": "",
        "matches": [],
        "context": "",
    }


def test_whitespace_modification_request_returns_empty_context():
    result = prepare_code_modification(
        db=None,
        repository_id=1,
        modification_request="   ",
    )

    assert result == {
        "repository_id": 1,
        "modification_request": "   ",
        "matches": [],
        "context": "",
    }


def test_code_modification_searches_repository():
    matches = [
        {
            "path": "hotel/views.py",
            "symbol_name": "room_has_booking_conflict",
            "start_line": 120,
            "end_line": 145,
            "relevance_score": 0.9234,
            "content": "def room_has_booking_conflict(...):",
        }
    ]

    with patch(
        "app.services.tools.code_modification_tool.search_code",
        return_value=matches,
    ) as mock_search:
        result = prepare_code_modification(
            db=None,
            repository_id=1,
            modification_request=(
                "Modify the room booking conflict logic."
            ),
            limit=5,
        )

    mock_search.assert_called_once_with(
        db=None,
        repository_id=1,
        query="Modify the room booking conflict logic.",
        limit=5,
    )

    assert result["repository_id"] == 1
    assert (
        result["modification_request"]
        == "Modify the room booking conflict logic."
    )
    assert result["matches"] == matches


def test_code_modification_builds_relevant_code_context():
    matches = [
        {
            "path": "hotel/views.py",
            "symbol_name": "room_has_booking_conflict",
            "start_line": 120,
            "end_line": 145,
            "relevance_score": 0.9234,
            "content": (
                "def room_has_booking_conflict(room, check_in, check_out):\n"
                "    return Booking.objects.filter(...).exists()"
            ),
        },
        {
            "path": "hotel/models.py",
            "symbol_name": "Booking",
            "start_line": 30,
            "end_line": 75,
            "relevance_score": 0.8123,
            "content": (
                "class Booking(models.Model):\n"
                "    room = models.ForeignKey(Room, ...)"
            ),
        },
    ]

    with patch(
        "app.services.tools.code_modification_tool.search_code",
        return_value=matches,
    ):
        result = prepare_code_modification(
            db=None,
            repository_id=1,
            modification_request="Modify booking conflict handling.",
        )

    assert "### Relevant Code 1" in result["context"]
    assert "File: hotel/views.py:120-145" in result["context"]
    assert (
        "Symbol: room_has_booking_conflict"
        in result["context"]
    )
    assert "Relevance: 0.9234" in result["context"]

    assert "### Relevant Code 2" in result["context"]
    assert "File: hotel/models.py:30-75" in result["context"]
    assert "Symbol: Booking" in result["context"]
    assert "Relevance: 0.8123" in result["context"]


def test_code_modification_handles_missing_line_numbers():
    matches = [
        {
            "path": "hotel/services.py",
            "symbol_name": "BookingService",
            "start_line": None,
            "end_line": None,
            "relevance_score": 0.7567,
            "content": "class BookingService:",
        }
    ]

    with patch(
        "app.services.tools.code_modification_tool.search_code",
        return_value=matches,
    ):
        result = prepare_code_modification(
            db=None,
            repository_id=1,
            modification_request="Modify BookingService.",
        )

    assert "File: hotel/services.py" in result["context"]
    assert "File: hotel/services.py:" not in result["context"]
    assert "Symbol: BookingService" in result["context"]


def test_code_modification_passes_custom_limit():
    with patch(
        "app.services.tools.code_modification_tool.search_code",
        return_value=[],
    ) as mock_search:
        result = prepare_code_modification(
            db=None,
            repository_id=7,
            modification_request="Update booking validation.",
            limit=10,
        )

    mock_search.assert_called_once_with(
        db=None,
        repository_id=7,
        query="Update booking validation.",
        limit=10,
    )

    assert result["matches"] == []
    assert result["context"] == ""


def test_code_modification_creates_proposal():
    proposal = {
        "repository_path": "workspace/test",
        "file_path": "app.py",
        "original_content": (
            "def hello():\n"
            "    return 'hello'\n"
        ),
        "proposed_content": (
            "def hello():\n"
            "    return 'hello world'\n"
        ),
        "diff": (
            "--- a/app.py\n"
            "+++ b/app.py\n"
            "-    return 'hello'\n"
            "+    return 'hello world'\n"
        ),
    }

    with patch(
        "app.services.tools.code_modification_tool._get_repository_workspace_path",
        return_value="workspace/test",
    ), patch(
        "app.services.tools.code_modification_tool.modification_service.prepare_modification",
        return_value=type(
            "Proposal",
            (),
            proposal,
        )(),
    ) as mock_prepare:
        result = prepare_code_modification(
            db=None,
            repository_id=1,
            modification_request="Change hello response.",
            file_path="app.py",
            proposed_content=(
                "def hello():\n"
                "    return 'hello world'\n"
            ),
        )

    mock_prepare.assert_called_once_with(
        repository_path="workspace/test",
        file_path="app.py",
        proposed_content=(
            "def hello():\n"
            "    return 'hello world'\n"
        ),
    )

    assert result["proposal"]["file_path"] == "app.py"
    assert result["proposal"]["diff"] != ""


def test_code_modification_requires_file_path_for_proposal():
    with pytest.raises(
        ValueError,
        match="file_path is required",
    ):
        prepare_code_modification(
            db=None,
            repository_id=1,
            modification_request="Change hello.",
            proposed_content="new content",
        )


def test_code_modification_requires_proposed_content_for_proposal():
    with pytest.raises(
        ValueError,
        match="proposed_content is required",
    ):
        prepare_code_modification(
            db=None,
            repository_id=1,
            modification_request="Change hello.",
            file_path="app.py",
        )


def test_code_modification_proposal_resolves_repository_workspace():
    with patch(
        "app.services.tools.code_modification_tool._get_repository_workspace_path",
        return_value="workspace/repository",
    ) as mock_workspace, patch(
        "app.services.tools.code_modification_tool.modification_service.prepare_modification",
    ) as mock_prepare:

        mock_prepare.return_value = type(
            "Proposal",
            (),
            {
                "repository_path": "workspace/repository",
                "file_path": "app.py",
                "original_content": "old",
                "proposed_content": "new",
                "diff": "-old\n+new\n",
            },
        )()

        result = prepare_code_modification(
            db=None,
            repository_id=42,
            modification_request="Update app.py.",
            file_path="app.py",
            proposed_content="new",
        )

    mock_workspace.assert_called_once_with(
        db=None,
        repository_id=42,
    )

    assert (
        result["proposal"]["repository_path"]
        == "workspace/repository"
    )


def test_code_modification_apply_changes_file(tmp_path: Path):
    target_file = tmp_path / "app.py"

    original_content = (
        "def hello():\n"
        "    return 'hello'\n"
    )

    proposed_content = (
        "def hello():\n"
        "    return 'hello world'\n"
    )

    target_file.write_text(
        original_content,
        encoding="utf-8",
    )

    with patch(
        "app.services.tools.code_modification_tool._get_repository_workspace_path",
        return_value=str(tmp_path),
    ):
        result = prepare_code_modification(
            db=None,
            repository_id=1,
            modification_request="Change hello response.",
            operation="apply",
            file_path="app.py",
            original_content=original_content,
            proposed_content=proposed_content,
        )

    assert result["operation"] == "apply"
    assert result["applied"] is True

    assert target_file.read_text(
        encoding="utf-8"
    ) == proposed_content


def test_code_modification_rollback_restores_file(tmp_path: Path):
    target_file = tmp_path / "app.py"

    original_content = (
        "def hello():\n"
        "    return 'hello'\n"
    )

    applied_content = (
        "def hello():\n"
        "    return 'hello world'\n"
    )

    target_file.write_text(
        applied_content,
        encoding="utf-8",
    )

    with patch(
        "app.services.tools.code_modification_tool._get_repository_workspace_path",
        return_value=str(tmp_path),
    ):
        result = prepare_code_modification(
            db=None,
            repository_id=1,
            modification_request="Rollback hello response.",
            operation="rollback",
            file_path="app.py",
            original_content=original_content,
            applied_content=applied_content,
        )

    assert result["operation"] == "rollback"
    assert result["rolled_back"] is True

    assert target_file.read_text(
        encoding="utf-8"
    ) == original_content


def test_code_modification_apply_detects_concurrent_change(
    tmp_path: Path,
):
    target_file = tmp_path / "app.py"

    original_content = "old\n"
    proposed_content = "new\n"
    concurrent_content = "someone else changed this\n"

    target_file.write_text(
        concurrent_content,
        encoding="utf-8",
    )

    with patch(
        "app.services.tools.code_modification_tool._get_repository_workspace_path",
        return_value=str(tmp_path),
    ):
        with pytest.raises(
            Exception,
            match="Target file changed",
        ):
            prepare_code_modification(
                db=None,
                repository_id=1,
                modification_request="Change app.py.",
                operation="apply",
                file_path="app.py",
                original_content=original_content,
                proposed_content=proposed_content,
            )

    assert target_file.read_text(
        encoding="utf-8"
    ) == concurrent_content


def test_code_modification_rollback_detects_newer_change(
    tmp_path: Path,
):
    target_file = tmp_path / "app.py"

    original_content = "old\n"
    applied_content = "new\n"
    newer_content = "newer change\n"

    target_file.write_text(
        newer_content,
        encoding="utf-8",
    )

    with patch(
        "app.services.tools.code_modification_tool._get_repository_workspace_path",
        return_value=str(tmp_path),
    ):
        with pytest.raises(
            Exception,
            match="Target file changed",
        ):
            prepare_code_modification(
                db=None,
                repository_id=1,
                modification_request="Rollback app.py.",
                operation="rollback",
                file_path="app.py",
                original_content=original_content,
                applied_content=applied_content,
            )

    assert target_file.read_text(
        encoding="utf-8"
    ) == newer_content


def test_code_modification_rejects_invalid_operation():
    with pytest.raises(
        ValueError,
        match="operation must be one of",
    ):
        prepare_code_modification(
            db=None,
            repository_id=1,
            modification_request="Change app.py.",
            operation="delete",
        )