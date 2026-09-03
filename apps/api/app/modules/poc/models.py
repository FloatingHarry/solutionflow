import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.poc.enums import (
    MetricOperator,
    MetricResultStatus,
    PocDecisionType,
    PocPlanStatus,
)
from app.modules.solutions.models import SolutionProposal


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


class PocPlan(Base):
    __tablename__ = "poc_plans"
    __table_args__ = (
        UniqueConstraint("solution_proposal_id", name="uq_poc_plans_solution_proposal"),
        Index("ix_poc_plans_account_status", "account_id", "status"),
        CheckConstraint("timeline_days > 0", name="ck_poc_plans_timeline_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    solution_proposal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("solution_proposals.id", ondelete="RESTRICT"), nullable=False
    )
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    business_problem: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    required_data: Mapped[list[str]] = mapped_column(json_column(), default=list, nullable=False)
    architecture: Mapped[str] = mapped_column(Text, nullable=False)
    timeline_days: Mapped[int] = mapped_column(Integer, default=14, nullable=False)
    evaluation_dataset: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    risks: Mapped[list[str]] = mapped_column(json_column(), default=list, nullable=False)
    status: Mapped[PocPlanStatus] = mapped_column(
        enum_column(PocPlanStatus), default=PocPlanStatus.DRAFT, nullable=False
    )
    review_notes: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    solution_proposal: Mapped[SolutionProposal] = relationship()
    metrics: Mapped[list["PocMetric"]] = relationship(
        back_populates="poc_plan",
        cascade="all, delete-orphan",
        order_by="PocMetric.position",
    )
    decisions: Mapped[list["PocDecision"]] = relationship(
        back_populates="poc_plan",
        cascade="all, delete-orphan",
        order_by="PocDecision.created_at.desc()",
    )


class PocMetric(Base):
    __tablename__ = "poc_metrics"
    __table_args__ = (
        UniqueConstraint("poc_plan_id", "metric_key", name="uq_poc_metrics_plan_key"),
        CheckConstraint("position >= 0", name="ck_poc_metrics_position_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    poc_plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("poc_plans.id", ondelete="CASCADE"), nullable=False
    )
    metric_key: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    target_operator: Mapped[MetricOperator] = mapped_column(
        enum_column(MetricOperator), nullable=False
    )
    target_value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    actual_value: Mapped[float | None] = mapped_column(Float)
    result_status: Mapped[MetricResultStatus] = mapped_column(
        enum_column(MetricResultStatus), default=MetricResultStatus.PENDING, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    poc_plan: Mapped[PocPlan] = relationship(back_populates="metrics")


class PocDecision(Base):
    __tablename__ = "poc_decisions"
    __table_args__ = (Index("ix_poc_decisions_plan_created", "poc_plan_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    poc_plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("poc_plans.id", ondelete="CASCADE"), nullable=False
    )
    decision: Mapped[PocDecisionType] = mapped_column(
        enum_column(PocDecisionType), nullable=False
    )
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    poc_plan: Mapped[PocPlan] = relationship(back_populates="decisions")
