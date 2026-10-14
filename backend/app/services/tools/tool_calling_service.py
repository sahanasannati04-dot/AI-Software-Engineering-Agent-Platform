import json

from app.services.llm.gemini_provider import GeminiProvider
from app.services.tools.tool_schemas import TOOL_SCHEMAS


TOOL_CALLING_SYSTEM_PROMPT = """
You are the tool-selection component of a professional AI software
engineering agent.

Your job is to decide whether the user's request requires one of the
available repository engineering tools and, when required, select the
correct tool and arguments.

Available tools:

{tools}

Return ONLY valid JSON.

If a tool is required:

{
  "action": "tool_call",
  "tool_name": "exact_tool_name",
  "arguments": {
    "argument_name": "argument_value"
  }
}

If no repository tool is required:

{
  "action": "direct_answer"
}

GENERAL RULES:
- Choose only tools from the provided list.
- Use the exact AI-facing tool names from the provided schema.
- Do not invent repository IDs.
- Do not invent filesystem paths.
- Do not invent file contents.
- Do not invent previous tool results.
- Do not execute tools yourself.
- Do not include markdown.
- Do not include explanations outside the JSON.
- Include only arguments that are supported by the selected tool.
- Use conversation history to resolve references such as "it",
  "this function", "that bug", "the previous change", or
  "the conflict check".
- If the request refers to repository code, prefer the appropriate
  repository engineering tool over a generic direct answer.
- For questions asking why repository code is failing or behaving
  incorrectly, prefer the bug-analysis tool.
- For requests to understand repository structure or metadata, prefer
  repository inspection.
- For requests to find relevant code, prefer code search.
- For requests about a specific file, prefer file inspection.
- For requests about a function, class, or method, prefer symbol inspection.

CODE MODIFICATION SAFETY RULES:

The code modification tool supports four operations:

1. context
2. prepare
3. apply
4. rollback

Use "context" when the user is asking to understand, locate, or gather
relevant code before proposing a modification.

Use "prepare" when the requested change is understood and the agent
needs to create a proposed modification and unified diff.

Use "apply" ONLY when a modification has already been prepared and the
required original content and proposed content are available from a
previous tool result or trusted conversation context.

Use "rollback" ONLY when a previously applied modification is explicitly
being reverted and the original content and applied content are available
from the previous modification result.

IMPORTANT:
- Never invent original_content.
- Never invent applied_content.
- Never invent proposed_content for an apply operation.
- Never invent a file path.
- Never skip the preparation stage merely because the user asks to
  "change" or "fix" code.
- A request to modify code should normally begin with context or prepare,
  not apply.
- Applying a modification is a state-changing operation and requires
  an existing prepared change.
- If the user asks to modify code but the exact target is unclear,
  use context or code_search first.
- If the user asks to review or propose a change without explicitly
  asking to apply it, use prepare rather than apply.
- If a modification has been prepared but the user has not approved
  applying it, do not select apply.
- If the user explicitly approves an already prepared modification,
  apply may be selected only when the original_content and
  proposed_content are available.
- If the user explicitly asks to undo an already applied change,
  rollback may be selected only when the required previous state is
  available.
- Preserve the diff when it is already available.
- Do not fabricate a diff.

MODIFICATION WORKFLOW:

Prefer this progression:

User request
→ understand target
→ context
→ prepare
→ proposed diff
→ explicit approval
→ apply
→ test execution
→ analyze test result
→ fix if necessary
→ retest
→ final report

Do not claim that code has been changed merely because a modification
was prepared.

TESTING RULES:
- After an applied code modification, prefer test execution when tests
  are available or when the changed behavior should be validated.
- If a test failure is reported, prefer bug analysis or code inspection
  before proposing another modification.
- Do not claim tests passed unless a test execution result actually
  indicates success.

MULTI-STEP REASONING:
- Use previous tool results in conversation history to determine what
  has already been inspected, prepared, applied, or tested.
- Avoid repeating the same tool call with identical arguments unless
  the previous result was insufficient.
- When a previous tool result provides the exact file path, repository
  ID, original content, proposed content, or diff, reuse that trusted
  information rather than inventing new values.
- If the next operation depends on information that is not available,
  select an inspection/context tool instead of guessing.

The tool-selection response must always be valid JSON and must contain
no additional text.
"""


# AI-facing schema names are mapped to the existing executable
# tool names used by the tool registry.
TOOL_NAME_ALIASES = {
    "code_search": "search_code",
    "repository_inspection": "inspect_repository",
    "file_inspection": "inspect_file",
    "symbol_inspection": "inspect_symbol",
    "test_generation": "generate_test_context",
    "bug_analysis": "prepare_bug_analysis",
    "code_explanation": "prepare_code_explanation",
    "code_modification": "prepare_code_modification",
    "test_execution": "prepare_test_execution",
}


def _normalize_tool_name(tool_name: str) -> str:
    """
    Convert an AI-facing schema tool name into the
    executable registry tool name.
    """

    return TOOL_NAME_ALIASES.get(
        tool_name,
        tool_name,
    )


def _get_valid_tool_names() -> set[str]:
    """
    Return the executable tool names represented by
    the AI-facing tool schemas.
    """

    return {
        TOOL_NAME_ALIASES.get(
            tool_name,
            tool_name,
        )
        for tool_name in TOOL_SCHEMAS
    }


def _validate_tool_arguments(result: dict) -> None:
    """
    Validate the basic structure of Gemini's selected tool arguments.

    Detailed argument validation remains the responsibility of the
    executable tool itself.
    """

    arguments = result.get("arguments")

    if not isinstance(arguments, dict):
        raise RuntimeError(
            "Gemini returned invalid tool arguments."
        )

    tool_name = result["tool_name"]

    if tool_name == "prepare_code_modification":
        operation = arguments.get("operation", "context")

        if operation not in {
            "context",
            "prepare",
            "apply",
            "rollback",
        }:
            raise RuntimeError(
                "Gemini returned an invalid code modification operation."
            )

        if operation in {
            "apply",
            "rollback",
        }:
            if not arguments.get("original_content"):
                raise RuntimeError(
                    "Code modification apply/rollback requires "
                    "trusted original_content."
                )

        if operation == "apply":
            if not arguments.get("proposed_content"):
                raise RuntimeError(
                    "Code modification apply requires "
                    "trusted proposed_content."
                )

        if operation == "rollback":
            if not arguments.get("applied_content"):
                raise RuntimeError(
                    "Code modification rollback requires "
                    "trusted applied_content."
                )


def select_tool(
    user_request: str,
    conversation_context: str = "",
) -> dict:
    """
    Ask Gemini whether a repository engineering tool is required.

    The AI-facing schema names are normalized into the existing
    executable tool registry names before returning the selection.
    """

    if not isinstance(
        user_request,
        str,
    ):
        raise ValueError(
            "user_request must be a string."
        )

    if not user_request.strip():
        return {
            "action": "direct_answer",
        }

    tools_text = json.dumps(
        TOOL_SCHEMAS,
        indent=2,
    )

    system_prompt = TOOL_CALLING_SYSTEM_PROMPT.replace(
        "{tools}",
        tools_text,
    )

    provider = GeminiProvider()

    prompt = user_request

    if conversation_context.strip():
        prompt = (
            f"Conversation history:\n"
            f"{conversation_context}\n\n"
            f"Current user request:\n"
            f"{user_request}"
        )

    response = provider.generate(
        prompt=prompt,
        system_prompt=system_prompt,
    )

    try:
        result = json.loads(response)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Gemini returned invalid tool-selection JSON."
        ) from exc

    if not isinstance(
        result,
        dict,
    ):
        raise RuntimeError(
            "Gemini returned an invalid tool-selection response."
        )

    if result.get("action") not in {
        "tool_call",
        "direct_answer",
    }:
        raise RuntimeError(
            "Gemini returned an invalid tool-selection action."
        )

    if result["action"] == "direct_answer":
        return {
            "action": "direct_answer",
        }

    if not result.get("tool_name"):
        raise RuntimeError(
            "Gemini did not provide a tool name."
        )

    raw_tool_name = result["tool_name"]

    if not isinstance(
        raw_tool_name,
        str,
    ):
        raise RuntimeError(
            "Gemini returned an invalid tool name."
        )

    normalized_tool_name = _normalize_tool_name(
        raw_tool_name
    )

    valid_tool_names = _get_valid_tool_names()

    if normalized_tool_name not in valid_tool_names:
        raise RuntimeError(
            "Gemini selected an unknown tool."
        )

    result["tool_name"] = normalized_tool_name

    _validate_tool_arguments(
        result
    )

    return result