"""ORM 모델: 사건·소스·댓글·판독·추가 답변. 삭제는 사건 기준으로 연쇄 삭제."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def utcnow() -> datetime:
    """UTC 현재 시각 (SQLite 저장용 naive UTC)."""
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("case"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    sources: Mapped[list[Source]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="Source.collected_at, Source.id"
    )
    comments: Mapped[list[Comment]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="Comment.seq"
    )
    answers: Mapped[list[Answer]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="Answer.id"
    )


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("src"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(16))  # youtube | text | image | url_only
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)  # STORAGE_DIR 기준 상대 경로
    mime_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    needs_manual_input: Mapped[bool] = mapped_column(Boolean, default=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    case: Mapped[Case] = relationship(back_populates="sources")
    comments: Mapped[list[Comment]] = relationship(
        back_populates="source", cascade="all, delete-orphan", order_by="Comment.seq"
    )


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("cmt"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    seq: Mapped[int] = mapped_column(Integer, default=0)
    author: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text)  # 원문. 수정 API 없음.
    posted_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    comment_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    platform: Mapped[str] = mapped_column(String(16))
    like_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parent_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    saved: Mapped[bool] = mapped_column(Boolean, default=False)
    user_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)

    case: Mapped[Case] = relationship(back_populates="comments")
    source: Mapped[Source] = relationship(back_populates="comments")
    analysis: Mapped[Analysis | None] = relationship(
        back_populates="comment", cascade="all, delete-orphan", uselist=False
    )


class Analysis(Base):
    __tablename__ = "analyses"

    comment_id: Mapped[str] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"), primary_key=True)
    level: Mapped[str] = mapped_column(String(16))
    level_label: Mapped[str] = mapped_column(String(64))
    issues: Mapped[list] = mapped_column(JSON, default=list)
    flagged_phrases: Mapped[list] = mapped_column(JSON, default=list)
    reason: Mapped[str] = mapped_column(Text)
    check_points: Mapped[list] = mapped_column(JSON, default=list)
    disclaimer: Mapped[str] = mapped_column(Text)
    # 선택(참고용) 필드. 이전 판독 결과에는 없을 수 있다.
    statement_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    related_laws: Mapped[list | None] = mapped_column(JSON, nullable=True)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    comment: Mapped[Comment] = relationship(back_populates="analysis")


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (UniqueConstraint("case_id", "question_id", name="uq_answer_case_question"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[str] = mapped_column(String(64))
    answer: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    case: Mapped[Case] = relationship(back_populates="answers")
