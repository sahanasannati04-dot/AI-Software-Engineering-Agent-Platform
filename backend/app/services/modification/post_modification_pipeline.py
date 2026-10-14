from dataclasses import dataclass

from app.services.validation.validation_service import (
    PostModificationValidationService,
    ValidationResult,
)


@dataclass
class ModificationValidationOutcome:
    """
    Result of validating a repository after a code modification.
    """

    modification_id: int | None
    validation: ValidationResult
    requires_bug_analysis: bool


class PostModificationPipeline:
    """
    Coordinates post-modification validation.

    Workflow:

        modification applied
            ↓
        run repository tests
            ↓
        tests pass → success
        tests fail → bug analysis required
        tests timeout → bug analysis required
    """

    def __init__(
        self,
        validation_service: PostModificationValidationService | None = None,
    ):
        self.validation_service = (
            validation_service
            if validation_service is not None
            else PostModificationValidationService()
        )

    def validate_modification(
        self,
        workspace_path: str,
        modification_id: int | None = None,
        test_target: str | None = None,
    ) -> ModificationValidationOutcome:
        validation = self.validation_service.validate(
            workspace_path=workspace_path,
            test_target=test_target,
        )

        requires_bug_analysis = not validation.passed

        return ModificationValidationOutcome(
            modification_id=modification_id,
            validation=validation,
            requires_bug_analysis=requires_bug_analysis,
        )

    def build_result(
        self,
        outcome: ModificationValidationOutcome,
    ) -> dict:
        """
        Convert the pipeline outcome into an agent-friendly result.
        """

        validation = outcome.validation

        result = {
            "modification_id": outcome.modification_id,
            "validation": {
                "status": validation.status,
                "passed": validation.passed,
                "exit_code": validation.exit_code,
                "command": validation.command,
                "stdout": validation.stdout,
                "stderr": validation.stderr,
                "timed_out": validation.timed_out,
            },
            "requires_bug_analysis": (
                outcome.requires_bug_analysis
            ),
        }

        if validation.passed:
            result["next_action"] = "complete"
        else:
            result["next_action"] = "bug_analysis"

        return result