from sqlalchemy.orm import Session

from app.services.conversation_service import get_conversation_messages


def build_conversation_context(
    db: Session,
    conversation_id: int,
    user_id: int,
    max_messages: int = 10,
) -> str:
    """
    Build a compact conversation history for the agent.
    """

    messages = get_conversation_messages(
        db=db,
        conversation_id=conversation_id,
        user_id=user_id,
    )

    if not messages:
        return ""

    recent_messages = messages[-max_messages:]

    sections = []

    for message in recent_messages:
        role = message.role.strip().lower()
        content = message.content.strip()

        if not content:
            continue

        sections.append(
            f"{role.upper()}: {content}"
        )

    return "\n".join(sections)