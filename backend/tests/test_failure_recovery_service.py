from unittest.mock import Mock, patch

from app.services.modification.failure_recovery_service import (
    FailureRecoveryContext,
    ModificationFailureRecoveryService,
)


def test_failure_recovery_analyzes_failed_validation():
    service = ModificationFailureRecoveryService()

    db = Mock()

    validation_result = {
        "modification_id": 42,
        "validation": {
            "status": "failed",
            "passed": False,
            "exit_code": 1,
            "stdout": "FAILED tests/test_booking.py::test_booking_conflict",
            "stderr": "AssertionError: booking conflict detected",
            "timed_out": False,
        },
        "requires_bug_analysis": True,
        "next_action": "bug_analysis",
    }

    analysis_result = {
        "repository_id": 1,
        "bug_description": "booking conflict failure",
        "matches": [
            {
                "path": "hotel/views.py",
                "start_line": 100,
                "end_line": 120,
                "symbol_name": "room_has_booking_conflict",
                "relevance_score": 0.94,
                "content": "def room_has_booking_conflict(): pass",
            }
        ],
        "context": (
            "### Possible Relevant Code 1\n"
            "File: hotel/views.py:100-120\n"
            "Symbol: room_has_booking_conflict"
        ),
    }

    with patch(
        "app.services.modification.failure_recovery_service.prepare_bug_analysis",
        return_value=analysis_result,
    ) as mock_analysis:
        result = service.analyze_failure(
            db=db,
            repository_id=1,
            modification_id=42,
            validation_result=validation_result,
        )

    assert isinstance(result, FailureRecoveryContext)

    assert result.modification_id == 42
    assert result.validation_status == "failed"
    assert result.requires_bug_analysis is True

    assert "Modification ID: 42" in result.bug_description
    assert "Validation status: failed" in result.bug_description
    assert "FAILED tests/test_booking.py" in result.test_output
    assert "AssertionError: booking conflict detected" in result.test_output

    assert len(result.matches) == 1
    assert result.matches[0]["path"] == "hotel/views.py"

    assert "room_has_booking_conflict" in result.context

    mock_analysis.assert_called_once_with(
        db=db,
        repository_id=1,
        bug_description=result.bug_description,
        limit=5,
    )


def test_failure_recovery_supports_custom_limit():
    service = ModificationFailureRecoveryService()

    db = Mock()

    validation_result = {
        "modification_id": 55,
        "validation": {
            "status": "timeout",
            "passed": False,
            "exit_code": 1,
            "stdout": "",
            "stderr": "Test execution timed out.",
            "timed_out": True,
        },
        "requires_bug_analysis": True,
        "next_action": "bug_analysis",
    }

    analysis_result = {
        "repository_id": 2,
        "bug_description": "timeout",
        "matches": [],
        "context": "",
    }

    with patch(
        "app.services.modification.failure_recovery_service.prepare_bug_analysis",
        return_value=analysis_result,
    ) as mock_analysis:
        result = service.analyze_failure(
            db=db,
            repository_id=2,
            modification_id=55,
            validation_result=validation_result,
            limit=10,
        )

    assert result.requires_bug_analysis is True
    assert result.validation_status == "timeout"
    assert "Test execution timed out." in result.test_output

    mock_analysis.assert_called_once_with(
        db=db,
        repository_id=2,
        bug_description=result.bug_description,
        limit=10,
    )


def test_failure_recovery_does_not_analyze_successful_validation():
    service = ModificationFailureRecoveryService()

    db = Mock()

    validation_result = {
        "modification_id": 77,
        "validation": {
            "status": "passed",
            "passed": True,
            "exit_code": 0,
            "stdout": "5 passed",
            "stderr": "",
            "timed_out": False,
        },
        "requires_bug_analysis": False,
        "next_action": "complete",
    }

    with patch(
        "app.services.modification.failure_recovery_service.prepare_bug_analysis"
    ) as mock_analysis:
        result = service.analyze_failure(
            db=db,
            repository_id=1,
            modification_id=77,
            validation_result=validation_result,
        )

    assert result.modification_id == 77
    assert result.validation_status == "passed"
    assert result.requires_bug_analysis is False
    assert result.matches == []
    assert result.context == ""
    assert "5 passed" in result.test_output

    mock_analysis.assert_not_called()


def test_failure_recovery_builds_result():
    service = ModificationFailureRecoveryService()

    context = FailureRecoveryContext(
        modification_id=42,
        bug_description="Validation failed.",
        context="Relevant repository code.",
        matches=[
            {
                "path": "hotel/views.py",
                "symbol_name": "create_booking",
            }
        ],
        validation_status="failed",
        test_output="AssertionError",
        requires_bug_analysis=True,
    )

    result = service.build_result(context)

    assert result == {
        "modification_id": 42,
        "validation_status": "failed",
        "requires_bug_analysis": True,
        "bug_description": "Validation failed.",
        "test_output": "AssertionError",
        "matches": [
            {
                "path": "hotel/views.py",
                "symbol_name": "create_booking",
            }
        ],
        "context": "Relevant repository code.",
        "next_action": "prepare_fix",
    }


def test_failure_recovery_builds_complete_result_for_success():
    service = ModificationFailureRecoveryService()

    context = FailureRecoveryContext(
        modification_id=42,
        bug_description="Validation passed.",
        context="",
        matches=[],
        validation_status="passed",
        test_output="5 passed",
        requires_bug_analysis=False,
    )

    result = service.build_result(context)

    assert result["modification_id"] == 42
    assert result["validation_status"] == "passed"
    assert result["requires_bug_analysis"] is False
    assert result["next_action"] == "complete"


def test_failure_recovery_rejects_invalid_validation_result():
    service = ModificationFailureRecoveryService()

    try:
        service.analyze_failure(
            db=Mock(),
            repository_id=1,
            modification_id=42,
            validation_result=None,
        )
        assert False
    except ValueError as exc:
        assert str(exc) == (
            "validation_result must be a dictionary."
        )


def test_failure_recovery_rejects_invalid_validation_section():
    service = ModificationFailureRecoveryService()

    try:
        service.analyze_failure(
            db=Mock(),
            repository_id=1,
            modification_id=42,
            validation_result={
                "validation": "invalid",
            },
        )
        assert False
    except ValueError as exc:
        assert str(exc) == (
            "validation_result.validation must be a dictionary."
        )


def test_failure_recovery_combines_stdout_and_stderr():
    service = ModificationFailureRecoveryService()

    validation_result = {
        "modification_id": 100,
        "validation": {
            "status": "failed",
            "passed": False,
            "exit_code": 1,
            "stdout": "Test output",
            "stderr": "Error output",
        },
    }

    analysis_result = {
        "repository_id": 1,
        "bug_description": "failure",
        "matches": [],
        "context": "",
    }

    with patch(
        "app.services.modification.failure_recovery_service.prepare_bug_analysis",
        return_value=analysis_result,
    ):
        result = service.analyze_failure(
            db=Mock(),
            repository_id=1,
            modification_id=100,
            validation_result=validation_result,
        )

    assert "Test stdout:\nTest output" in result.test_output
    assert "Test stderr:\nError output" in result.test_output