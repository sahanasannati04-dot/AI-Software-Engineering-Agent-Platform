from dataclasses import dataclass

from app.services.tools.bug_analysis_tool import (
    prepare_bug_analysis,
)


@dataclass
class FailureRecoveryContext:
    """
    Context produced after a post-modification validation failure.

    This object contains enough information for the agent to
    understand the failure and decide whether a corrective
    modification should be prepared.
    """

    modification_id: int | None
    bug_description: str
    context: str
    matches: list[dict]
    validation_status: str
    test_output: str
    requires_bug_analysis: bool


class ModificationFailureRecoveryService:
    """
    Builds bug-analysis context after a modification fails validation.

    This service is read-only. It does not modify repository files.
    Any corrective modification must continue through the existing
    prepare → approval → apply → validate workflow.
    """

    def analyze_failure(
        self,
        db,
        repository_id: int,
        modification_id: int | None,
        validation_result: dict,
        limit: int = 5,
    ) -> FailureRecoveryContext:
        if not isinstance(validation_result, dict):
            raise ValueError(
                "validation_result must be a dictionary."
            )

        validation = validation_result.get(
            "validation",
            {},
        )

        if not isinstance(validation, dict):
            raise ValueError(
                "validation_result.validation must be a dictionary."
            )

        status = validation.get(
            "status",
            "failed",
        )

        passed = validation.get(
            "passed",
            False,
        )

        stdout = validation.get(
            "stdout",
            "",
        )

        stderr = validation.get(
            "stderr",
            "",
        )

        test_output = self._build_test_output(
            stdout=stdout,
            stderr=stderr,
        )

        bug_description = self._build_bug_description(
            modification_id=modification_id,
            validation_status=status,
            test_output=test_output,
        )

        if passed:
            return FailureRecoveryContext(
                modification_id=modification_id,
                bug_description=bug_description,
                context="",
                matches=[],
                validation_status=status,
                test_output=test_output,
                requires_bug_analysis=False,
            )

        analysis = prepare_bug_analysis(
            db=db,
            repository_id=repository_id,
            bug_description=bug_description,
            limit=limit,
        )

        return FailureRecoveryContext(
            modification_id=modification_id,
            bug_description=bug_description,
            context=analysis["context"],
            matches=analysis["matches"],
            validation_status=status,
            test_output=test_output,
            requires_bug_analysis=True,
        )

    @staticmethod
    def _build_test_output(
        stdout: str,
        stderr: str,
    ) -> str:
        sections = []

        if isinstance(stdout, str) and stdout.strip():
            sections.append(
                f"Test stdout:\n{stdout.strip()}"
            )

        if isinstance(stderr, str) and stderr.strip():
            sections.append(
                f"Test stderr:\n{stderr.strip()}"
            )

        return "\n\n".join(sections)

    @staticmethod
    def _build_bug_description(
        modification_id: int | None,
        validation_status: str,
        test_output: str,
    ) -> str:
        modification_text = (
            str(modification_id)
            if modification_id is not None
            else "unknown"
        )

        description = (
            "Post-modification validation failed. "
            f"Modification ID: {modification_text}. "
            f"Validation status: {validation_status}."
        )

        if test_output:
            description += (
                "\n\nValidation output:\n"
                f"{test_output}"
            )

        return description

    def build_result(
        self,
        context: FailureRecoveryContext,
    ) -> dict:
        """
        Convert recovery context into an agent-friendly result.
        """

        return {
            "modification_id": context.modification_id,
            "validation_status": context.validation_status,
            "requires_bug_analysis": (
                context.requires_bug_analysis
            ),
            "bug_description": context.bug_description,
            "test_output": context.test_output,
            "matches": context.matches,
            "context": context.context,
            "next_action": (
                "prepare_fix"
                if context.requires_bug_analysis
                else "complete"
            ),
        }