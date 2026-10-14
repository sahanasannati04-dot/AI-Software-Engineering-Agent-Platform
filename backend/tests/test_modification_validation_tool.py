from unittest.mock import Mock, patch

from app.services.tools.modification_validation_tool import (
    validate_code_modification,
)


@patch(
    "app.services.tools.modification_validation_tool.validation_service"
)
def test_validate_code_modification(mock_validation_service):
    db = Mock()

    mock_validation_service.validate_applied_modification.return_value = {
        "modification_id": 10,
        "repository_id": 1,
        "validation": {
            "status": "passed",
            "passed": True,
            "exit_code": 0,
        },
        "requires_bug_analysis": False,
        "next_action": "complete",
        "modification_status": "validated",
        "file_path": "app/example.py",
    }

    result = validate_code_modification(
        db=db,
        repository_id=1,
        modification_id=10,
    )

    assert result["modification_id"] == 10
    assert result["validation"]["passed"] is True
    assert result["next_action"] == "complete"

    mock_validation_service.validate_applied_modification.assert_called_once_with(
        db=db,
        repository_id=1,
        modification_id=10,
        test_target=None,
    )


@patch(
    "app.services.tools.modification_validation_tool.validation_service"
)
def test_validate_code_modification_with_test_target(
    mock_validation_service,
):
    db = Mock()

    mock_validation_service.validate_applied_modification.return_value = {
        "modification_id": 10,
        "repository_id": 1,
        "validation": {
            "status": "passed",
            "passed": True,
            "exit_code": 0,
        },
        "requires_bug_analysis": False,
        "next_action": "complete",
    }

    result = validate_code_modification(
        db=db,
        repository_id=1,
        modification_id=10,
        test_target="tests/test_example.py",
    )

    assert result["validation"]["passed"] is True

    mock_validation_service.validate_applied_modification.assert_called_once_with(
        db=db,
        repository_id=1,
        modification_id=10,
        test_target="tests/test_example.py",
    )


def test_validate_code_modification_rejects_invalid_repository_id():
    db = Mock()

    try:
        validate_code_modification(
            db=db,
            repository_id="1",
            modification_id=10,
        )
        assert False
    except ValueError as exc:
        assert str(exc) == "repository_id must be an integer."


def test_validate_code_modification_rejects_invalid_modification_id():
    db = Mock()

    try:
        validate_code_modification(
            db=db,
            repository_id=1,
            modification_id="10",
        )
        assert False
    except ValueError as exc:
        assert str(exc) == "modification_id must be an integer."


def test_validate_code_modification_rejects_invalid_test_target():
    db = Mock()

    try:
        validate_code_modification(
            db=db,
            repository_id=1,
            modification_id=10,
            test_target=123,
        )
        assert False
    except ValueError as exc:
        assert str(exc) == "test_target must be a string."


def test_validate_code_modification_rejects_null_byte():
    db = Mock()

    try:
        validate_code_modification(
            db=db,
            repository_id=1,
            modification_id=10,
            test_target="tests\x00/test.py",
        )
        assert False
    except ValueError as exc:
        assert str(exc) == (
            "test_target contains an invalid character."
        )