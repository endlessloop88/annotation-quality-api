from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Annotator(Base):
    __tablename__ = "annotators"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    project: Mapped[str] = mapped_column(String(100), index=True)
    guideline_version: Mapped[str] = mapped_column(String(20), default="v1")
    prompt: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (UniqueConstraint("task_id", "annotator_id", "attempt"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    annotator_id: Mapped[int] = mapped_column(ForeignKey("annotators.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    # submitted -> accepted | rework | rejected
    status: Mapped[str] = mapped_column(String(20), default="submitted", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    review: Mapped[Optional["Review"]] = relationship(back_populates="submission", uselist=False)


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"), unique=True)
    reviewer: Mapped[str] = mapped_column(String(100))
    decision: Mapped[str] = mapped_column(String(20))
    score: Mapped[int] = mapped_column(Integer)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    submission: Mapped["Submission"] = relationship(back_populates="review")
