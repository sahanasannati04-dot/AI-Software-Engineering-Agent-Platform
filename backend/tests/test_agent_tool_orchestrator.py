from unittest.mock import Mock, patch

from app.services.agent_tool_orchestrator import (
    MAX_AGENT_STEPS,
    MAX_MODIFICATION_RECOVERY_ATTEMPTS,
    run_agent_tool,
)


def test_direct_answer_without_tool():
    with patch(
        "app.services.agent_tool_orchestrator.select_tool",
        return_value={
            "action": "direct_answer",
        },
    ):
        result = run_agent_tool(
            db=None,
            repository_id=1,
            user_request="What does this project do?",
        )

    assert result == {
        "action": "direct_answer",
        "result": None,
        "steps": [],
    }


def test_single_tool_execution():
    selection = {
        "action": "tool_call",
        "tool_name": "search_code",
        "arguments": {
            "query": "booking conflict",
            "limit": 5,
        },
    }

    tool_result = {
        "matches": [
            {
                "path": "hotel/views.py",
                "symbol_name": "booking",
            }
        ]
    }

    with patch(
        "app.services.agent_tool_orchestrator.select_tool",
        return_value=selection,
    ), patch(
        "app.services.agent_tool_orchestrator.execute_tool",
        return_value=tool_result,
    ) as mock_execute:
        result = run_agent_tool(
            db=None,
            repository_id=1,
            user_request="Find booking conflict code.",
        )

    assert result["action"] == "tool_call"
    assert result["tool_name"] == "search_code"
    assert result["result"] == tool_result
    assert len(result["steps"]) == 1

    mock_execute.assert_called_once_with(
        "search_code",
        {
            "db": None,
            "repository_id": 1,
            "query": "booking conflict",
            "limit": 5,
        },
    )


def test_multi_step_tool_execution():
    selections = [
        {
            "action": "tool_call",
            "tool_name": "search_code",
            "arguments": {
                "query": "booking conflict",
                "limit": 5,
            },
        },
        {
            "action": "tool_call",
            "tool_name": "inspect_file",
            "arguments": {
                "file_path": "hotel/views.py",
            },
        },
        {
            "action": "direct_answer",
        },
    ]

    tool_results = [
        {
            "matches": [
                {
                    "path": "hotel/views.py",
                }
            ]
        },
        {
            "path": "hotel/views.py",
            "content": "booking code",
        },
    ]

    with patch(
        "app.services.agent_tool_orchestrator.select_tool",
        side_effect=selections,
    ), patch(
        "app.services.agent_tool_orchestrator.execute_tool",
        side_effect=tool_results,
    ):
        result = run_agent_tool(
            db=None,
            repository_id=1,
            user_request="Inspect booking conflict code.",
        )

    assert result["action"] == "tool_call"
    assert result["tool_name"] == "inspect_file"
    assert result["result"] == tool_results[1]
    assert len(result["steps"]) == 2


def test_repeated_identical_tool_call_stops():
    selection = {
        "action": "tool_call",
        "tool_name": "search_code",
        "arguments": {
            "query": "booking",
            "limit": 5,
        },
    }

    tool_result = {
        "matches": [],
    }

    with patch(
        "app.services.agent_tool_orchestrator.select_tool",
        side_effect=[
            selection,
            selection,
        ],
    ), patch(
        "app.services.agent_tool_orchestrator.execute_tool",
        return_value=tool_result,
    ) as mock_execute:
        result = run_agent_tool(
            db=None,
            repository_id=1,
            user_request="Find booking code.",
        )

    assert len(result["steps"]) == 1
    mock_execute.assert_called_once()


def test_max_agent_steps_is_enforced():
    selection = {
        "action": "tool_call",
        "tool_name": "search_code",
        "arguments": {
            "query": "booking",
            "limit": 5,
        },
    }

    tool_results = [
        {"step": index}
        for index in range(MAX_AGENT_STEPS)
    ]

    with patch(
        "app.services.agent_tool_orchestrator.select_tool",
        return_value=selection,
    ), patch(
        "app.services.agent_tool_orchestrator.execute_tool",
        side_effect=tool_results,
    ):
        result = run_agent_tool(
            db=None,
            repository_id=1,
            user_request="Keep searching.",
        )

    assert len(result["steps"]) == MAX_AGENT_STEPS


def test_code_modification_apply_requires_approval():
    selection = {
        "action": "tool_call",
        "tool_name": "prepare_code_modification",
        "arguments": {
            "operation": "apply",
            "file_path": "hotel/views.py",
            "modification_request": "Apply the prepared change.",
            "original_content": "original",
            "proposed_content": "updated",
        },
    }

    with patch(
        "app.services.agent_tool_orchestrator.select_tool",
        return_value=selection,
    ):
        result = run_agent_tool(
            db=None,
            repository_id=1,
            user_request="Apply the prepared change.",
            approved=False,
        )

    assert result["action"] == "approval_required"
    assert result["approval_required"] is True
    assert result["tool_name"] == "prepare_code_modification"
    assert result["arguments"]["operation"] == "apply"


def test_code_modification_rollback_requires_approval():
    selection = {
        "action": "tool_call",
        "tool_name": "prepare_code_modification",
        "arguments": {
            "operation": "rollback",
            "file_path": "hotel/views.py",
            "modification_request": "Rollback the change.",
            "original_content": "original",
            "applied_content": "updated",
        },
    }

    with patch(
        "app.services.agent_tool_orchestrator.select_tool",
        return_value=selection,
    ):
        result = run_agent_tool(
            db=None,
            repository_id=1,
            user_request="Rollback the change.",
            approved=False,
        )

    assert result["action"] == "approval_required"
    assert result["approval_required"] is True
    assert result["tool_name"] == "prepare_code_modification"
    assert result["arguments"]["operation"] == "rollback"


def test_code_modification_apply_with_approval_executes_and_validates():
    selection = {
        "action": "tool_call",
        "tool_name": "prepare_code_modification",
        "arguments": {
            "operation": "apply",
            "file_path": "hotel/views.py",
            "modification_request": "Apply the prepared change.",
            "original_content": "original",
            "proposed_content": "updated",
        },
    }

    apply_result = {
        "operation": "apply",
        "applied": True,
        "modification_id": 42,
        "status": "applied",
    }

    validation_result = {
        "modification_id": 42,
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
        "modification_status": "validated",
    }

    with patch(
        "app.services.agent_tool_orchestrator.select_tool",
        side_effect=[
            selection,
            {
                "action": "direct_answer",
            },
        ],
    ), patch(
        "app.services.agent_tool_orchestrator.execute_tool",
        side_effect=[
            apply_result,
            validation_result,
        ],
    ) as mock_execute:
        result = run_agent_tool(
            db=None,
            repository_id=1,
            user_request="Apply the prepared change.",
            approved=True,
        )

    assert result["action"] == "tool_call"
    assert result["tool_name"] == (
        "validate_code_modification"
    )
    assert result["result"] == validation_result

    assert len(result["steps"]) == 2

    assert result["steps"][0]["tool_name"] == (
        "prepare_code_modification"
    )
    assert result["steps"][1]["tool_name"] == (
        "validate_code_modification"
    )

    mock_execute.assert_any_call(
        "validate_code_modification",
        {
            "db": None,
            "repository_id": 1,
            "modification_id": 42,
        },
    )


def test_code_modification_apply_validation_failure_requests_bug_analysis():
    selection = {
        "action": "tool_call",
        "tool_name": "prepare_code_modification",
        "arguments": {
            "operation": "apply",
            "file_path": "hotel/views.py",
            "modification_request": "Apply the prepared change.",
            "original_content": "original",
            "proposed_content": "updated",
        },
    }

    apply_result = {
        "operation": "apply",
        "applied": True,
        "modification_id": 55,
        "status": "applied",
    }

    validation_result = {
        "modification_id": 55,
        "validation": {
            "status": "failed",
            "passed": False,
            "exit_code": 1,
            "stdout": "FAILED test_booking",
            "stderr": "AssertionError",
            "timed_out": False,
        },
        "requires_bug_analysis": True,
        "next_action": "bug_analysis",
        "modification_status": "validation_failed",
    }

    recovery_result = {
        "modification_id": 55,
        "validation_status": "failed",
        "requires_bug_analysis": True,
        "bug_description": (
            "Post-modification validation failed."
        ),
        "test_output": (
            "Test stdout:\nFAILED test_booking\n\n"
            "Test stderr:\nAssertionError"
        ),
        "matches": [
            {
                "path": "hotel/views.py",
                "symbol_name": "create_booking",
            }
        ],
        "context": "Relevant booking code.",
        "next_action": "prepare_fix",
    }

    with patch(
        "app.services.agent_tool_orchestrator.select_tool",
        side_effect=[
            selection,
            {
                "action": "direct_answer",
            },
        ],
    ), patch(
        "app.services.agent_tool_orchestrator.execute_tool",
        side_effect=[
            apply_result,
            validation_result,
        ],
    ) as mock_execute, patch(
        "app.services.agent_tool_orchestrator._run_failure_recovery",
        return_value=recovery_result,
    ) as mock_recovery:
        result = run_agent_tool(
            db=None,
            repository_id=1,
            user_request="Apply the prepared change.",
            approved=True,
        )

    assert result["action"] == "tool_call"

    assert result["tool_name"] == "failure_recovery"

    assert result["result"] == recovery_result

    assert result["steps"][0]["tool_name"] == (
        "prepare_code_modification"
    )

    assert result["steps"][1]["tool_name"] == (
        "validate_code_modification"
    )

    assert result["steps"][2]["tool_name"] == (
        "failure_recovery"
    )

    assert (
        result["steps"][2]["result"]["next_action"]
        == "prepare_fix"
    )

    mock_execute.assert_any_call(
        "validate_code_modification",
        {
            "db": None,
            "repository_id": 1,
            "modification_id": 55,
        },
    )

    mock_recovery.assert_called_once()


def test_approval_is_consumed_after_one_state_changing_operation():
    selections = [
        {
            "action": "tool_call",
            "tool_name": "prepare_code_modification",
            "arguments": {
                "operation": "apply",
                "file_path": "hotel/views.py",
                "modification_request": "Apply change.",
                "original_content": "original",
                "proposed_content": "updated",
                "modification_id": 10,
            },
        },
        {
            "action": "tool_call",
            "tool_name": "search_code",
            "arguments": {
                "query": "booking",
                "limit": 5,
            },
        },
    ]

    apply_result = {
        "operation": "apply",
        "applied": True,
        "modification_id": 10,
        "status": "applied",
    }

    validation_result = {
        "modification_id": 10,
        "validation": {
            "status": "passed",
            "passed": True,
            "exit_code": 0,
            "stdout": "passed",
            "stderr": "",
            "timed_out": False,
        },
        "requires_bug_analysis": False,
        "next_action": "complete",
    }

    search_result = {
        "matches": [],
    }

    with patch(
        "app.services.agent_tool_orchestrator.select_tool",
        side_effect=selections,
    ), patch(
        "app.services.agent_tool_orchestrator.execute_tool",
        side_effect=[
            apply_result,
            validation_result,
            search_result,
        ],
    ):
        result = run_agent_tool(
            db=None,
            repository_id=1,
            user_request="Apply change and search booking code.",
            approved=True,
        )

    assert len(result["steps"]) == 3
    assert result["steps"][0]["tool_name"] == (
        "prepare_code_modification"
    )
    assert result["steps"][1]["tool_name"] == (
        "validate_code_modification"
    )
    assert result["steps"][2]["tool_name"] == (
        "search_code"
    )


def test_prepared_modification_id_is_propagated_to_apply():
    selections = [
        {
            "action": "tool_call",
            "tool_name": "prepare_code_modification",
            "arguments": {
                "operation": "prepare",
                "file_path": "hotel/views.py",
                "proposed_content": "updated",
            },
        },
        {
            "action": "tool_call",
            "tool_name": "prepare_code_modification",
            "arguments": {
                "operation": "apply",
                "file_path": "hotel/views.py",
            },
        },
    ]

    prepare_result = {
        "operation": "prepare",
        "repository_id": 1,
        "modification_id": 99,
        "status": "prepared",
        "approval_required": True,
        "proposal": {
            "file_path": "hotel/views.py",
            "original_content": "original",
            "proposed_content": "updated",
            "diff": "--- diff",
        },
    }

    apply_result = {
        "operation": "apply",
        "repository_id": 1,
        "applied": True,
        "modification_id": 99,
        "status": "applied",
    }

    validation_result = {
        "modification_id": 99,
        "validation": {
            "status": "passed",
            "passed": True,
            "exit_code": 0,
            "stdout": "passed",
            "stderr": "",
            "timed_out": False,
        },
        "requires_bug_analysis": False,
        "next_action": "complete",
    }

    with patch(
        "app.services.agent_tool_orchestrator.select_tool",
        side_effect=selections,
    ), patch(
        "app.services.agent_tool_orchestrator.execute_tool",
        side_effect=[
            prepare_result,
            apply_result,
            validation_result,
        ],
    ) as mock_execute:
        result = run_agent_tool(
            db=None,
            repository_id=1,
            user_request="Prepare and apply the change.",
            approved=True,
        )

    assert result["steps"][1]["arguments"]["modification_id"] == 99

    mock_execute.assert_any_call(
        "prepare_code_modification",
        {
            "db": None,
            "repository_id": 1,
            "operation": "apply",
            "file_path": "hotel/views.py",
            "modification_id": 99,
            "original_content": "original",
            "proposed_content": "updated",
            "diff": "--- diff",
        },
    )


def test_prepared_modification_id_is_propagated_to_rollback():
    selections = [
        {
            "action": "tool_call",
            "tool_name": "prepare_code_modification",
            "arguments": {
                "operation": "prepare",
                "file_path": "hotel/views.py",
                "proposed_content": "updated",
            },
        },
        {
            "action": "tool_call",
            "tool_name": "prepare_code_modification",
            "arguments": {
                "operation": "rollback",
                "file_path": "hotel/views.py",
            },
        },
    ]

    prepare_result = {
        "operation": "prepare",
        "repository_id": 1,
        "modification_id": 101,
        "status": "prepared",
        "approval_required": True,
        "proposal": {
            "file_path": "hotel/views.py",
            "original_content": "original",
            "proposed_content": "updated",
            "diff": "--- diff",
        },
    }

    rollback_result = {
        "operation": "rollback",
        "repository_id": 1,
        "rolled_back": True,
        "modification_id": 101,
        "status": "rolled_back",
    }

    with patch(
        "app.services.agent_tool_orchestrator.select_tool",
        side_effect=selections,
    ), patch(
        "app.services.agent_tool_orchestrator.execute_tool",
        side_effect=[
            prepare_result,
            rollback_result,
        ],
    ) as mock_execute:
        result = run_agent_tool(
            db=None,
            repository_id=1,
            user_request="Prepare and rollback the change.",
            approved=True,
        )

    assert result["steps"][1]["arguments"]["modification_id"] == 101

    mock_execute.assert_any_call(
        "prepare_code_modification",
        {
            "db": None,
            "repository_id": 1,
            "operation": "rollback",
            "file_path": "hotel/views.py",
            "modification_id": 101,
            "original_content": "original",
            "applied_content": "updated",
            "diff": "--- diff",
        },
    )


def test_orchestrator_does_not_invent_modification_id():
    selection = {
        "action": "tool_call",
        "tool_name": "prepare_code_modification",
        "arguments": {
            "operation": "apply",
            "file_path": "hotel/views.py",
            "original_content": "original",
            "proposed_content": "updated",
        },
    }

    apply_result = {
        "operation": "apply",
        "applied": True,
        "status": "applied",
    }

    with patch(
        "app.services.agent_tool_orchestrator.select_tool",
        return_value=selection,
    ), patch(
        "app.services.agent_tool_orchestrator.execute_tool",
        return_value=apply_result,
    ):
        try:
            run_agent_tool(
                db=None,
                repository_id=1,
                user_request="Apply change.",
                approved=True,
            )
            assert False
        except ValueError as exc:
            assert str(exc) == (
                "Applied modification did not return a valid "
                "modification_id."
            )


def test_failure_recovery_attempt_limit_is_configured():
    assert MAX_MODIFICATION_RECOVERY_ATTEMPTS == 2


def test_failure_recovery_is_not_triggered_after_successful_validation():
    selection = {
        "action": "tool_call",
        "tool_name": "prepare_code_modification",
        "arguments": {
            "operation": "apply",
            "file_path": "hotel/views.py",
            "original_content": "original",
            "proposed_content": "updated",
        },
    }

    apply_result = {
        "operation": "apply",
        "applied": True,
        "modification_id": 120,
        "status": "applied",
    }

    validation_result = {
        "modification_id": 120,
        "validation": {
            "status": "passed",
            "passed": True,
            "exit_code": 0,
            "stdout": "10 passed",
            "stderr": "",
            "timed_out": False,
        },
        "requires_bug_analysis": False,
        "next_action": "complete",
    }

    with patch(
        "app.services.agent_tool_orchestrator.select_tool",
        side_effect=[
            selection,
            {
                "action": "direct_answer",
            },
        ],
    ), patch(
        "app.services.agent_tool_orchestrator.execute_tool",
        side_effect=[
            apply_result,
            validation_result,
        ],
    ), patch(
        "app.services.agent_tool_orchestrator._run_failure_recovery",
    ) as mock_recovery:
        result = run_agent_tool(
            db=None,
            repository_id=1,
            user_request="Apply the prepared change.",
            approved=True,
        )

    assert result["tool_name"] == (
        "validate_code_modification"
    )
    assert len(result["steps"]) == 2
    mock_recovery.assert_not_called()