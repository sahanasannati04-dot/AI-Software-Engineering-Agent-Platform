import json

from app.services.agent_tool_orchestrator import run_agent_tool
from app.services.llm.gemini_provider import GeminiProvider


FINAL_ANSWER_SYSTEM_PROMPT = """
You are the final response component of an AI software engineering agent.

Answer the user's current request using:
1. The conversation history, when provided.
2. All repository tool execution results, when provided.
3. The complete execution history when multiple tools were used.

Rules:
- Be accurate and grounded in the available context.
- Use conversation history to resolve references such as "it", "this function",
  "that bug", "the previous issue", or "the conflict check".
- Use all relevant tool results together when forming the answer.
- Do not invent files, symbols, line numbers, or implementation details.
- If a tool result contains source code, explain only what is supported by that code.
- Mention relevant file paths and line numbers when available.
- If a tool result indicates that something was not found, say so clearly.
- Distinguish confirmed findings from reasonable conclusions.
- Do not mention internal tool orchestration unless it is relevant.
- Give a concise, professional software-engineering answer.
"""


def answer_with_tools(
    db,
    repository_id: int,
    user_request: str,
    conversation_context: str = "",
) -> dict:
    """
    Run the conversation-aware multi-step agent pipeline
    and generate the final grounded answer.
    """

    tool_result = run_agent_tool(
        db=db,
        repository_id=repository_id,
        user_request=user_request,
        conversation_context=conversation_context,
    )

    provider = GeminiProvider()

    if tool_result["action"] == "direct_answer":
        prompt = user_request

        if conversation_context.strip():
            prompt = (
                f"Conversation history:\n"
                f"{conversation_context}\n\n"
                f"Current user request:\n"
                f"{user_request}"
            )

        answer = provider.generate(
            prompt=prompt,
            system_prompt=FINAL_ANSWER_SYSTEM_PROMPT,
        )

        return {
            "action": "direct_answer",
            "answer": answer,
            "tool_name": None,
            "tool_result": None,
            "steps": [],
        }

    execution_history = tool_result.get(
        "steps",
        [],
    )

    prompt = (
        f"Conversation history:\n"
        f"{conversation_context or '(none)'}\n\n"
        f"Current user request:\n"
        f"{user_request}\n\n"
        f"Repository investigation history:\n"
        f"{json.dumps(execution_history, indent=2, default=str)}"
    )

    answer = provider.generate(
        prompt=prompt,
        system_prompt=FINAL_ANSWER_SYSTEM_PROMPT,
    )

    return {
        "action": "tool_call",
        "answer": answer,
        "tool_name": tool_result["tool_name"],
        "tool_result": tool_result["result"],
        "steps": execution_history,
    }
