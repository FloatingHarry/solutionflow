import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class SystemEvaluationRun(Base):
    __tablename__ = "system_evaluation_runs"
    __table_args__ = (
        Index("ix_system_evaluation_runs_created", "created_at"),
        CheckConstraint("total_tasks >= 0", name="ck_system_evaluation_total_tasks"),
        CheckConstraint("passed_tasks >= 0", name="ck_system_evaluation_passed_tasks"),
        CheckConstraint(
            "pass_rate >= 0 AND pass_rate <= 100", name="ck_system_evaluation_pass_rate"
        ),
        CheckConstraint(
            "hallucination_rate >= 0 AND hallucination_rate <= 100",
            name="ck_system_evaluation_hallucination_rate",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    methodology: Mapped[str] = mapped_column(Text, nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(80), nullable=False)
    is_deterministic: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    demo_account_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_tasks: Mapped[int] = mapped_column(Integer, nullable=False)
    passed_tasks: Mapped[int] = mapped_column(Integer, nullable=False)
    pass_rate: Mapped[float] = mapped_column(Float, nullable=False)
    hallucination_rate: Mapped[float] = mapped_column(Float, nullable=False)
    citation_correctness: Mapped[float] = mapped_column(Float, nullable=False)
    task_completion_rate: Mapped[float] = mapped_column(Float, nullable=False)
    mean_latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    tasks: Mapped[list["SystemEvaluationTask"]] = relationship(
        back_populates="evaluation_run",
        cascade="all, delete-orphan",
        order_by="SystemEvaluationTask.position",
    )


class SystemEvaluationTask(Base):
    __tablename__ = "system_evaluation_tasks"
    __table_args__ = (
        Index("ix_system_evaluation_tasks_run_category", "evaluation_run_id", "category"),
        CheckConstraint("score >= 0 AND score <= 100", name="ck_system_evaluation_task_score"),
        CheckConstraint("position >= 0", name="ck_system_evaluation_task_position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    evaluation_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("system_evaluation_runs.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(240), nullable=False)
    expected: Mapped[str] = mapped_column(Text, nullable=False)
    actual: Mapped[str] = mapped_column(Text, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    evaluation_run: Mapped[SystemEvaluationRun] = relationship(back_populates="tasks")
