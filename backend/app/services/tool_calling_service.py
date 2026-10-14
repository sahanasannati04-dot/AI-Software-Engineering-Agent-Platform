import json

from app.services.llm.gemini_provider import GeminiProvider
from app.services.tools.tool_schemas import TOOL_SCHEMAS


TOOL_CALLING_SYSTEM_PROMPT = """
You are the tool-selection component of an AI software engineering agent.

Your job is to decide whether the user's request requires
one of the available repository engineering tools.

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

If no tool is required:

{
  "action": "direct_answer"
}

Rules:
- Choose only tools from the provided list.
- Use exact tool names.
- Include only arguments required by the selected tool.
- Use the conversation history to resolve references such as "it",
  "this function", "that bug", or "the conflict check".
- If the current request refers to repository code discussed earlier,
  select the appropriate repository tool.
- Prefer a repository tool over a direct answer whenever the request
  asks about the behavior, implementation, bug, location, or modification
  of code in the repository.
- For questions asking why repository code is failing or behaving incorrectly,
  prefer prepare_bug_analysis.
- After a code modification has been successfully applied, use
  modification_validation when the request requires verifying that the
  repository still passes its tests.
- modification_validation requires the persisted modification_id returned
  by the code modification workflow.
- Do not invent repository IDs, modification IDs, or filesystem paths.
- Do not execute tools yourself.
- Do not include markdown.
- Do not include explanations outside the JSON.
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
    "modification_validation": "validate_code_modification",
}


def _normalize_tool_name(
    tool_name: str,
) -> str:
    """
    Convert an AI-facing schema tool name into the
    executable registry tool name.
    """

    return TOOL_NAME_ALIASES.get(
        tool_name,
        tool_name,
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

    if result.get("action") not in {
        "tool_call",
        "direct_answer",
    }:
        raise RuntimeError(
            "Gemini returned an invalid tool-selection action."
        )

    if result["action"] == "tool_call":
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

        valid_tool_names = {
            TOOL_NAME_ALIASES.get(
                tool_name,
                tool_name,
            )
            for tool_name in TOOL_SCHEMAS
        }

        if normalized_tool_name not in valid_tool_names:
            raise RuntimeError(
                "Gemini selected an unknown tool."
            )

        result["tool_name"] = normalized_tool_name

        if not isinstance(
            result.get("arguments"),
            dict,
        ):
            raise RuntimeError(
                "Gemini returned invalid tool arguments."
            )

    return result