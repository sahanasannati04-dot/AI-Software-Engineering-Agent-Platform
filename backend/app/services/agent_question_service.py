from app.services.agent_intent_service import classify_intent
from app.services.agent_response_service import answer_with_tools
from app.services.conversation_context_service import (
    build_conversation_context,
)
from app.services.conversation_service import (
    add_message,
    get_conversation,
)


def answer_agent_question(
    db,
    repository_id: int,
    question: str,
    conversation_id: int | None = None,
    user_id: int | None = None,
) -> dict:
    """
    Run a repository question through the multi-step
    AI software engineering agent.
    """

    if not question.strip():
        return {
            "answer": "Please provide a repository question.",
            "intent": "general_question",
            "intent_confidence": 1.0,
            "steps": [],
        }

    # ---------------------------------------------------------
    # 1. Detect user intent
    # ---------------------------------------------------------

    intent_result = classify_intent(question)

    # ---------------------------------------------------------
    # 2. Validate conversation ownership
    # ---------------------------------------------------------

    conversation = None

    if conversation_id is not None:

        if user_id is None:
            raise ValueError(
                "user_id is required when conversation_id is provided."
            )

        conversation = get_conversation(
            db=db,
            conversation_id=conversation_id,
            user_id=user_id,
        )

        if not conversation:
            raise ValueError(
                "Conversation not found."
            )

        if conversation.repository_id != repository_id:
            raise ValueError(
                "Conversation does not belong to this repository."
            )

    # ---------------------------------------------------------
    # 3. Build conversation context
    # ---------------------------------------------------------

    conversation_context = ""

    if conversation is not None:
        conversation_context = build_conversation_context(
            db=db,
            conversation_id=conversation.id,
            user_id=user_id,
            max_messages=10,
        )

    # ---------------------------------------------------------
    # 4. Run multi-step engineering agent
    # ---------------------------------------------------------

    result = answer_with_tools(
        db=db,
        repository_id=repository_id,
        user_request=question,
        conversation_context=conversation_context,
    )

    # ---------------------------------------------------------
    # 5. Save conversation memory
    # ---------------------------------------------------------

    if conversation is not None:

        add_message(
            db=db,
            conversation_id=conversation.id,
            role="user",
            content=question,
        )

        add_message(
            db=db,
            conversation_id=conversation.id,
            role="assistant",
            content=result["answer"],
        )

    # ---------------------------------------------------------
    # 6. Return structured result
    # ---------------------------------------------------------

    return {
        "answer": result["answer"],
        "intent": intent_result.intent.value,
        "intent_confidence": intent_result.confidence,
        "steps": result.get("steps", []),
    }
