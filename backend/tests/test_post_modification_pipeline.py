from unittest.mock import Mock

from app.services.modification.post_modification_pipeline import (
    PostModificationPipeline,
)
from app.services.validation.validation_service import (
    ValidationResult,
)


def test_pipeline_marks_success_when_tests_pass():
    validation_service = Mock()

    validation_service.validate.return_value = ValidationResult(
        passed=True,
        exit_code=0,
        command=["python", "-m", "pytest"],
        stdout="5 passed",
        stderr="",
        timed_out=False,
        status="passed",
    )

    pipeline = PostModificationPipeline(
        validation_service=validation_service,
    )

    outcome = pipeline.validate_modification(
        workspace_path="C:\\workspace",
        modification_id=42,
    )

    assert outcome.modification_id == 42
    assert outcome.validation.passed is True
    assert outcome.requires_bug_analysis is False


def test_pipeline_requests_bug_analysis_when_tests_fail():
    validation_service = Mock()

    validation_service.validate.return_value = ValidationResult(
        passed=False,
        exit_code=1,
        command=["python", "-m", "pytest"],
        stdout="",
        stderr="AssertionError",
        timed_out=False,
        status="failed",
    )

    pipeline = PostModificationPipeline(
        validation_service=validation_service,
    )

    outcome = pipeline.validate_modification(
        workspace_path="C:\\workspace",
        modification_id=42,
    )

    assert outcome.modification_id == 42
    assert outcome.validation.passed is False
    assert outcome.requires_bug_analysis is True


def test_pipeline_requests_bug_analysis_on_timeout():
    validation_service = Mock()

    validation_service.validate.return_value = ValidationResult(
        passed=False,
        exit_code=-1,
        command=["python", "-m", "pytest"],
        stdout="",
        stderr="timeout",
        timed_out=True,
        status="timeout",
    )

    pipeline = PostModificationPipeline(
        validation_service=validation_service,
    )

    outcome = pipeline.validate_modification(
        workspace_path="C:\\workspace",
        modification_id=42,
    )

    assert outcome.validation.timed_out is True
    assert outcome.requires_bug_analysis is True


def test_pipeline_builds_success_result():
    validation_service = Mock()

    validation_service.validate.return_value = ValidationResult(
        passed=True,
        exit_code=0,
        command=["python", "-m", "pytest"],
        stdout="5 passed",
        stderr="",
        timed_out=False,
        status="passed",
    )

    pipeline = PostModificationPipeline(
        validation_service=validation_service,
    )

    outcome = pipeline.validate_modification(
        workspace_path="C:\\workspace",
        modification_id=42,
    )

    result = pipeline.build_result(outcome)

    assert result["modification_id"] == 42
    assert result["validation"]["status"] == "passed"
    assert result["validation"]["passed"] is True
    assert result["requires_bug_analysis"] is False
    assert result["next_action"] == "complete"


def test_pipeline_builds_failure_result():
    validation_service = Mock()

    validation_service.validate.return_value = ValidationResult(
        passed=False,
        exit_code=1,
        command=["python", "-m", "pytest"],
        stdout="",
        stderr="AssertionError",
        timed_out=False,
        status="failed",
    )

    pipeline = PostModificationPipeline(
        validation_service=validation_service,
    )

    outcome = pipeline.validate_modification(
        workspace_path="C:\\workspace",
        modification_id=42,
    )

    result = pipeline.build_result(outcome)

    assert result["modification_id"] == 42
    assert result["validation"]["status"] == "failed"
    assert result["validation"]["passed"] is False
    assert result["requires_bug_analysis"] is True
    assert result["next_action"] == "bug_analysis"


def test_pipeline_passes_test_target():
    validation_service = Mock()

    validation_service.validate.return_value = ValidationResult(
        passed=True,
        exit_code=0,
        command=[
            "python",
            "-m",
            "pytest",
            "tests/test_example.py",
        ],
        stdout="1 passed",
        stderr="",
        timed_out=False,
        status="passed",
    )

    pipeline = PostModificationPipeline(
        validation_service=validation_service,
    )

    pipeline.validate_modification(
        workspace_path="C:\\workspace",
        modification_id=7,
        test_target="tests/test_example.py",
    )

    validation_service.validate.assert_called_once_with(
        workspace_path="C:\\workspace",
        test_target="tests/test_example.py",
    )