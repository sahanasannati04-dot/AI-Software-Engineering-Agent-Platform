from unittest.mock import Mock

from app.services.modification.modification_validation_service import (
    ModificationValidationService,
)
from app.services.modification.post_modification_pipeline import (
    ModificationValidationOutcome,
)
from app.services.validation.validation_service import (
    ValidationResult,
)


def test_validate_applied_modification_passes():
    db = Mock()

    modification = Mock()
    modification.status = "applied"
    modification.file_path = "app/example.py"

    db.scalar.return_value = modification

    pipeline = Mock()

    validation = ValidationResult(
        passed=True,
        exit_code=0,
        command=["python", "-m", "pytest"],
        stdout="10 passed",
        stderr="",
        timed_out=False,
        status="passed",
    )

    pipeline.validate_modification.return_value = (
        ModificationValidationOutcome(
            modification_id=10,
            validation=validation,
            requires_bug_analysis=False,
        )
    )

    pipeline.build_result.return_value = {
        "modification_id": 10,
        "validation": {
            "status": "passed",
            "passed": True,
        },
        "requires_bug_analysis": False,
        "next_action": "complete",
    }

    service = ModificationValidationService(
        validation_pipeline=pipeline,
    )

    service._get_workspace_path = Mock(
        return_value="C:\\workspace"
    )

    result = service.validate_applied_modification(
        db=db,
        repository_id=1,
        modification_id=10,
    )

    assert result["validation"]["passed"] is True
    assert result["next_action"] == "complete"
    assert result["modification_status"] == "validated"

    pipeline.validate_modification.assert_called_once_with(
        workspace_path="C:\\workspace",
        modification_id=10,
        test_target=None,
    )

    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(modification)


def test_validate_applied_modification_failure():
    db = Mock()

    modification = Mock()
    modification.status = "applied"
    modification.file_path = "app/example.py"

    db.scalar.return_value = modification

    pipeline = Mock()

    validation = ValidationResult(
        passed=False,
        exit_code=1,
        command=["python", "-m", "pytest"],
        stdout="",
        stderr="AssertionError",
        timed_out=False,
        status="failed",
    )

    pipeline.validate_modification.return_value = (
        ModificationValidationOutcome(
            modification_id=10,
            validation=validation,
            requires_bug_analysis=True,
        )
    )

    pipeline.build_result.return_value = {
        "modification_id": 10,
        "validation": {
            "status": "failed",
            "passed": False,
        },
        "requires_bug_analysis": True,
        "next_action": "bug_analysis",
    }

    service = ModificationValidationService(
        validation_pipeline=pipeline,
    )

    service._get_workspace_path = Mock(
        return_value="C:\\workspace"
    )

    result = service.validate_applied_modification(
        db=db,
        repository_id=1,
        modification_id=10,
    )

    assert result["validation"]["passed"] is False
    assert result["requires_bug_analysis"] is True
    assert result["next_action"] == "bug_analysis"
    assert result["modification_status"] == "validation_failed"

    db.commit.assert_called_once()


def test_validation_rejects_non_applied_modification():
    db = Mock()

    modification = Mock()
    modification.status = "prepared"

    db.scalar.return_value = modification

    service = ModificationValidationService()

    try:
        service.validate_applied_modification(
            db=db,
            repository_id=1,
            modification_id=10,
        )
        assert False
    except ValueError as exc:
        assert str(exc) == (
            "Only an applied modification can be validated."
        )


def test_validation_rejects_unknown_modification():
    db = Mock()
    db.scalar.return_value = None

    service = ModificationValidationService()

    try:
        service.validate_applied_modification(
            db=db,
            repository_id=1,
            modification_id=999,
        )
        assert False
    except ValueError as exc:
        assert str(exc) == (
            "Code modification record not found."
        )