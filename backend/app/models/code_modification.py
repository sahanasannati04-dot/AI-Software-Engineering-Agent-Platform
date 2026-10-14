from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now_naive() -> datetime:
    """Return the current UTC time as a timezone-naive datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CodeModification(Base):
    __tablename__ = "code_modifications"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    repository_id: Mapped[int] = mapped_column(
        ForeignKey(
            "repositories.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    file_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="prepared",
        nullable=False,
        index=True,
    )

    original_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    proposed_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    applied_content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    diff: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    approval_required: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )

    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    rolled_back_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now_naive,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now_naive,
        onupdate=utc_now_naive,
        nullable=False,
    )

    repository: Mapped["Repository"] = relationship(
        back_populates="code_modifications",
    )
