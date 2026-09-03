import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.modules.agent.enums import AgentActionStatus, AgentProvider, AgentRunStatus


def utc_now() -> datetime:
    return datetime.now(UTC)


def enum_column(enum_type: type) -> Enum:
    return Enum(
        enum_type,
        values_callable=lambda members: [member.value for member in members],
        native_enum=False,
        validate_strings=True,
        create_constraint=True,
    )


def json_column() -> JSON:
    return JSON().with_variant(JSONB, "postgresql")


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        Index("ix_agent_runs_account_created", "account_id", "created_at"),
        Index("ix_agent_runs_account_status", "account_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[AgentRunStatus] = mapped_column(enum_column(AgentRunStatus), nullable=False)
    provider: Mapped[AgentProvider] = mapped_column(enum_column(AgentProvider), nullable=False)
    model: Mapped[str | None] = mapped_column(String(120))
    provider_response_id: Mapped[str | None] = mapped_column(String(160))
    stage_snapshot: Mapped[str] = mapped_column(String(80), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    observations: Mapped[list[str]] = mapped_column(json_column(), default=list, nullable=False)
    plan: Mapped[list[str]] = mapped_column(json_column(), default=list, nullable=False)
    question: Mapped[str | None] = mapped_column(Text)
    trace: Mapped[list[dict[str, Any]]] = mapped_column(json_column(), default=list, nullable=False)
    action_key: Mapped[str | None] = mapped_column(String(100))
    action_title: Mapped[str | None] = mapped_column(String(240))
    action_description: Mapped[str | None] = mapped_column(Text)
    action_reason: Mapped[str | None] = mapped_column(Text)
    action_target_path: Mapped[str | None] = mapped_column(String(500))
    action_requires_approval: Mapped[bool] = mapped_column(default=False, nullable=False)
    action_status: Mapped[AgentActionStatus] = mapped_column(
        enum_column(AgentActionStatus), default=AgentActionStatus.NONE, nullable=False
    )
    action_result: Mapped[dict[str, Any]] = mapped_column(
        json_column(), default=dict, nullable=False
    )
    approval_note: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
