from __future__ import annotations

from typing import Any

from app.services.tool_calling_service import select_tool
from app.services.tools.executor import execute_tool


MAX_AGENT_STEPS = 5
MAX_MODIFICATION_RECOVERY_ATTEMPTS = 2

STATE_CHANGING_TOOL = "prepare_code_modification"

STATE_CHANGING_OPERATIONS = {
    "apply",
    "rollback",
}

READ_ONLY_OPERATIONS = {
    "context",
    "prepare",
}


def _is_state_changing_operation(
    tool_name: str,
    arguments: dict[str, Any],
) -> bool:
    return (
        tool_name == STATE_CHANGING_TOOL
        and arguments.get("operation")
        in STATE_CHANGING_OPERATIONS
    )


def _requires_approval(
    tool_name: str,
    arguments: dict[str, Any],
) -> bool:
    return _is_state_changing_operation(
        tool_name,
        arguments,
    )


def _is_successful_apply(
    tool_name: str,
    arguments: dict[str, Any],
    result: Any,
) -> bool:
    if tool_name != STATE_CHANGING_TOOL:
        return False

    if arguments.get("operation") != "apply":
        return False

    if not isinstance(result, dict):
        return False

    return result.get("applied") is True


def _extract_modification_id(result: Any) -> int:
    if not isinstance(result, dict):
        raise ValueError(
            "Applied modification did not return a valid "
            "modification_id."
        )

    modification_id = result.get("modification_id")

    if not isinstance(modification_id, int):
        raise ValueError(
            "Applied modification did not return a valid "
            "modification_id."
        )

    return modification_id


def _build_validation_arguments(
    repository_id: int,
    apply_result: Any,
) -> dict[str, Any]:
    return {
        "db": None,
        "repository_id": repository_id,
        "modification_id": _extract_modification_id(
            apply_result
        ),
    }


def _build_prepared_operation_arguments(
    arguments: dict[str, Any],
    prepared_result: dict[str, Any],
) -> dict[str, Any]:
    updated_arguments = dict(arguments)

    modification_id = prepared_result.get(
        "modification_id"
    )

    if isinstance(modification_id, int):
        updated_arguments["modification_id"] = (
            modification_id
        )

    proposal = prepared_result.get("proposal")

    if not isinstance(proposal, dict):
        return updated_arguments

    operation = arguments.get("operation")

    original_content = proposal.get(
        "original_content"
    )
    proposed_content = proposal.get(
        "proposed_content"
    )
    applied_content = proposal.get(
        "applied_content"
    )
    diff = proposal.get("diff")

    if original_content is not None:
        updated_arguments["original_content"] = (
            original_content
        )

    if diff is not None:
        updated_arguments["diff"] = diff

    if operation == "apply":
        if proposed_content is not None:
            updated_arguments["proposed_content"] = (
                proposed_content
            )

        # Apply must not receive applied_content.
        updated_arguments.pop(
            "applied_content",
            None,
        )

    elif operation == "rollback":
        # Rollback needs the content that was applied.
        # A prepared proposal has not necessarily stored a
        # separate applied_content yet, so proposed_content
        # represents what would have been applied.
        if applied_content is not None:
            updated_arguments["applied_content"] = (
                applied_content
            )
        elif proposed_content is not None:
            updated_arguments["applied_content"] = (
                proposed_content
            )

        # Rollback must not receive proposed_content.
        updated_arguments.pop(
            "proposed_content",
            None,
        )

    return updated_arguments


def _validation_passed(result: Any) -> bool:
    if not isinstance(result, dict):
        return False

    validation = result.get("validation")

    if not isinstance(validation, dict):
        return False

    return validation.get("passed") is True


def _validation_failed(result: Any) -> bool:
    if not isinstance(result, dict):
        return False

    validation = result.get("validation")

    if not isinstance(validation, dict):
        return False

    return validation.get("passed") is False


def _is_same_selection(
    first: dict[str, Any] | None,
    second: dict[str, Any],
) -> bool:
    if first is None:
        return False

    return first == second


def _is_terminal_repeated_search(
    tool_name: str,
    result: Any,
) -> bool:
    if tool_name != "search_code":
        return False

    if not isinstance(result, dict):
        return False

    return "matches" in result


def _run_failure_recovery(
    db: Any,
    repository_id: int,
    modification_id: int | None,
    validation_result: dict[str, Any],
) -> dict[str, Any]:
    from app.services.modification.failure_recovery_service import (
        ModificationFailureRecoveryService,
    )

    recovery_service = ModificationFailureRecoveryService()

    context = recovery_service.analyze_failure(
        db=db,
        repository_id=repository_id,
        modification_id=modification_id,
        validation_result=validation_result,
    )

    return recovery_service.build_result(context)


def run_agent_tool(
    db: Any,
    repository_id: int,
    user_request: str,
    approved: bool = False,
) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []

    prepared_modification: dict[str, Any] | None = None

    previous_selection: dict[str, Any] | None = None
    previous_result: Any = None

    approval_available = approved
    state_change_completed = False

    recovery_attempts = 0

    for _ in range(MAX_AGENT_STEPS):
        selection = select_tool(
            db=db,
            repository_id=repository_id,
            user_request=user_request,
        )

        if not isinstance(selection, dict):
            return {
                "action": "direct_answer",
                "result": selection,
                "steps": steps,
            }

        if selection.get("action") == "direct_answer":
            if not steps:
                return {
                    "action": "direct_answer",
                    "result": selection.get("result"),
                    "steps": [],
                }

            return {
                "action": "tool_call",
                "tool_name": steps[-1]["tool_name"],
                "result": steps[-1]["result"],
                "steps": steps,
            }

        if selection.get("action") != "tool_call":
            return {
                "action": selection.get("action"),
                "result": selection.get("result"),
                "steps": steps,
            }

        tool_name = selection.get("tool_name")

        if not isinstance(tool_name, str):
            raise ValueError(
                "Tool selection did not contain a valid tool name."
            )

        raw_arguments = selection.get("arguments")

        if not isinstance(raw_arguments, dict):
            raw_arguments = {}

        arguments = dict(raw_arguments)

        arguments.setdefault("db", db)
        arguments.setdefault(
            "repository_id",
            repository_id,
        )

        operation = arguments.get("operation")

        current_selection = {
            "action": "tool_call",
            "tool_name": tool_name,
            "arguments": {
                key: value
                for key, value in arguments.items()
                if key != "db"
            },
        }

        if (
            _is_same_selection(
                previous_selection,
                current_selection,
            )
            and _is_terminal_repeated_search(
                tool_name,
                previous_result,
            )
        ):
            return {
                "action": "tool_call",
                "tool_name": steps[-1]["tool_name"],
                "result": steps[-1]["result"],
                "steps": steps,
            }

        if (
            tool_name == STATE_CHANGING_TOOL
            and operation in {"apply", "rollback"}
            and prepared_modification is not None
        ):
            arguments = _build_prepared_operation_arguments(
                arguments,
                prepared_modification,
            )

            current_selection = {
                "action": "tool_call",
                "tool_name": tool_name,
                "arguments": {
                    key: value
                    for key, value in arguments.items()
                    if key != "db"
                },
            }

        if _requires_approval(
            tool_name,
            arguments,
        ):
            if not approval_available:
                return {
                    "action": "approval_required",
                    "approval_required": True,
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "steps": steps,
                }

        result = execute_tool(
            tool_name,
            arguments,
        )

        step = {
            "tool_name": tool_name,
            "arguments": arguments,
            "result": result,
        }

        steps.append(step)

        if (
            tool_name == STATE_CHANGING_TOOL
            and operation == "prepare"
            and isinstance(result, dict)
        ):
            if isinstance(
                result.get("modification_id"),
                int,
            ):
                prepared_modification = result

            previous_selection = current_selection
            previous_result = result

            continue

        if (
            tool_name == STATE_CHANGING_TOOL
            and operation == "rollback"
        ):
            approval_available = False

            return {
                "action": "tool_call",
                "tool_name": tool_name,
                "result": result,
                "steps": steps,
            }

        if _is_successful_apply(
            tool_name,
            arguments,
            result,
        ):
            approval_available = False
            state_change_completed = True

            validation_arguments = _build_validation_arguments(
                repository_id,
                result,
            )

            validation_result = execute_tool(
                "validate_code_modification",
                validation_arguments,
            )

            steps.append(
                {
                    "tool_name": "validate_code_modification",
                    "arguments": validation_arguments,
                    "result": validation_result,
                }
            )

            if _validation_failed(validation_result):
                if (
                    recovery_attempts
                    >= MAX_MODIFICATION_RECOVERY_ATTEMPTS
                ):
                    return {
                        "action": "tool_call",
                        "tool_name": (
                            "validate_code_modification"
                        ),
                        "result": validation_result,
                        "steps": steps,
                    }

                recovery_attempts += 1

                recovery_result = _run_failure_recovery(
                    db=db,
                    repository_id=repository_id,
                    modification_id=result.get(
                        "modification_id"
                    ),
                    validation_result=validation_result,
                )

                steps.append(
                    {
                        "tool_name": "failure_recovery",
                        "arguments": {
                            "repository_id": repository_id,
                            "modification_id": result.get(
                                "modification_id"
                            ),
                        },
                        "result": recovery_result,
                    }
                )

                return {
                    "action": "tool_call",
                    "tool_name": "failure_recovery",
                    "result": recovery_result,
                    "steps": steps,
                }

            if (
                _validation_passed(validation_result)
                and prepared_modification is not None
            ):
                return {
                    "action": "tool_call",
                    "tool_name": (
                        "validate_code_modification"
                    ),
                    "result": validation_result,
                    "steps": steps,
                }

            previous_selection = {
                "action": "tool_call",
                "tool_name": (
                    "validate_code_modification"
                ),
                "arguments": {
                    "repository_id": repository_id,
                    "modification_id": result.get(
                        "modification_id"
                    ),
                },
            }

            previous_result = validation_result

            continue

        if state_change_completed:
            return {
                "action": "tool_call",
                "tool_name": tool_name,
                "result": result,
                "steps": steps,
            }

        previous_selection = current_selection
        previous_result = result

    if steps:
        return {
            "action": "tool_call",
            "tool_name": steps[-1]["tool_name"],
            "result": steps[-1]["result"],
            "steps": steps,
        }

    return {
        "action": "direct_answer",
        "result": None,
        "steps": [],
    }