from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.conversation_message import ConversationMessage


def create_conversation(
    db: Session,
    user_id: int,
    repository_id: int | None = None,
    title: str | None = None,
) -> Conversation:

    conversation = Conversation(
        user_id=user_id,
        repository_id=repository_id,
        title=title,
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


def add_message(
    db: Session,
    conversation_id: int,
    role: str,
    content: str,
) -> ConversationMessage:

    message = ConversationMessage(
        conversation_id=conversation_id,
        role=role,
        content=content,
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return message


def get_conversation(
    db: Session,
    conversation_id: int,
    user_id: int,
) -> Conversation | None:

    return db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )


def get_conversation_messages(
    db: Session,
    conversation_id: int,
    user_id: int,
) -> list[ConversationMessage]:

    conversation = get_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=user_id,
    )

    if not conversation:
        return []

    return list(conversation.messages)