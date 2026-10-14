from app.services.agent_intent_service import classify_intent
from app.services.conversation_service import (
    add_message,
    get_conversation,
)
from app.services.llm.gemini_provider import GeminiProvider
from app.services.repository_intelligence.rag_context import (
    build_rag_context,
)


def answer_repository_question(
    db,
    repository_id: int,
    question: str,
    limit: int = 5,
    conversation_id: int | None = None,
    user_id: int | None = None,
) -> dict:

    if not question.strip():
        return {
            "answer": "Please provide a repository question.",
            "sources": [],
            "intent": "general_question",
            "intent_confidence": 1.0,
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
    # 3. Retrieve relevant repository context
    # ---------------------------------------------------------

    rag_context = build_rag_context(
        db=db,
        repository_id=repository_id,
        query=question,
        limit=limit,
    )

    if not rag_context.chunks:
        return {
            "answer": (
                "I could not find relevant code in this repository "
                "to answer the question."
            ),
            "sources": [],
            "intent": intent_result.intent.value,
            "intent_confidence": intent_result.confidence,
        }

    # ---------------------------------------------------------
    # 4. Build conversation history
    # ---------------------------------------------------------

    conversation_history = ""

    if conversation is not None:

        messages = list(
            conversation.messages
        )

        if messages:

            history_sections = []

            for message in messages[-10:]:
                history_sections.append(
                    f"{message.role.upper()}: "
                    f"{message.content}"
                )

            conversation_history = (
                "\n\n"
                "Previous conversation:\n"
                + "\n".join(history_sections)
            )

    # ---------------------------------------------------------
    # 5. AI system instructions
    # ---------------------------------------------------------

    system_prompt = """
You are an AI software engineering assistant.

Answer questions about the repository using the provided
code context, detected user intent, and conversation history.

Rules:
- Base your answer on the provided repository context.
- Use previous conversation messages when they provide
  useful context for the current question.
- Consider the detected intent when deciding how to answer.
- Do not invent files, functions, classes, or behavior.
- If the repository context is insufficient, clearly say so.
- Explain the answer clearly and concisely.
- Mention relevant file paths and symbols when useful.
- For every important technical claim, identify the
  relevant source file and symbol.
- Prefer exact source references such as
  `hotel/views.py:room_has_booking_conflict`.
- Do not cite a source that does not support the claim.
- Do not claim that code exists unless it appears in the
  provided context.
- For code search requests, identify the relevant files
  and symbols.
- For code explanation requests, explain the implementation
  using the available source code.
- For bug analysis requests, identify possible causes only
  when supported by the repository context.
- For code modification requests, explain the required
  changes before making any assumptions.
- For test generation requests, base tests on the actual
  repository code shown in the context.
- For test execution requests, do not claim tests were run
  unless execution results are actually provided.
- For repository inspection requests, describe only the
  repository information supported by the retrieved context.
"""

    # ---------------------------------------------------------
    # 6. Build final prompt
    # ---------------------------------------------------------

    prompt = (
        f"Detected intent:\n"
        f"{intent_result.intent.value}\n\n"
        f"Intent confidence:\n"
        f"{intent_result.confidence:.2f}\n\n"
        f"Repository question:\n"
        f"{question}\n\n"
        f"{conversation_history}\n\n"
        f"Repository code context:\n"
        f"{rag_context.context_text}"
    )

    # ---------------------------------------------------------
    # 7. Generate AI answer
    # ---------------------------------------------------------

    provider = GeminiProvider()

    answer = provider.generate(
        prompt=prompt,
        system_prompt=system_prompt,
    )

    # ---------------------------------------------------------
    # 8. Save conversation memory
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
            content=answer,
        )

    # ---------------------------------------------------------
    # 9. Build structured source attribution
    # ---------------------------------------------------------

    sources = []

    for chunk in rag_context.chunks:

        sources.append(
            {
                "path": chunk.path,
                "symbol_name": chunk.symbol_name,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "chunk_type": chunk.chunk_type,
                "relevance_score": chunk.relevance_score,
            }
        )

    # ---------------------------------------------------------
    # 10. Return complete result
    # ---------------------------------------------------------

    return {
        "answer": answer,
        "sources": sources,
        "intent": intent_result.intent.value,
        "intent_confidence": intent_result.confidence,
    }