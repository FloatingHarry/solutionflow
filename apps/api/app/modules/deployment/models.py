import uuid
from datetime import UTC, date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.business_case.models import BusinessCase
from app.modules.deployment.enums import ChecklistItemStatus, DeploymentPlanStatus
from app.modules.solutions.enums import DeploymentOption


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


class DeploymentPlan(Base):
    __tablename__ = "deployment_plans"
    __table_args__ = (
        UniqueConstraint("account_id", name="uq_deployment_plans_account"),
        UniqueConstraint("business_case_id", name="uq_deployment_plans_business_case"),
        Index("ix_deployment_plans_status", "status", "updated_at"),
        CheckConstraint(
            "readiness_score >= 0 AND readiness_score <= 100",
            name="ck_deployment_plans_readiness_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    business_case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("business_cases.id", ondelete="RESTRICT"), nullable=False
    )
    environment: Mapped[DeploymentOption] = mapped_column(
        enum_column(DeploymentOption), nullable=False
    )
    owner: Mapped[str] = mapped_column(String(200), nullable=False)
    target_launch_date: Mapped[date | None] = mapped_column(Date)
    rollout_strategy: Mapped[str] = mapped_column(Text, nullable=False)
    integration_plan: Mapped[str] = mapped_column(Text, nullable=False)
    data_governance_plan: Mapped[str] = mapped_column(Text, nullable=False)
    monitoring_plan: Mapped[str] = mapped_column(Text, nullable=False)
    rollback_plan: Mapped[str] = mapped_column(Text, nullable=False)
    support_model: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[DeploymentPlanStatus] = mapped_column(
        enum_column(DeploymentPlanStatus),
        default=DeploymentPlanStatus.IN_PROGRESS,
        nullable=False,
    )
    readiness_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_notes: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    business_case: Mapped[BusinessCase] = relationship()
    checklist_items: Mapped[list["DeploymentChecklistItem"]] = relationship(
        back_populates="deployment_plan",
        cascade="all, delete-orphan",
        order_by="DeploymentChecklistItem.position",
    )


class DeploymentChecklistItem(Base):
    __tablename__ = "deployment_checklist_items"
    __table_args__ = (
        UniqueConstraint(
            "deployment_plan_id", "category", name="uq_deployment_checklist_plan_category"
        ),
        CheckConstraint("position >= 0", name="ck_deployment_checklist_position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    deployment_plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("deployment_plans.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    owner: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[ChecklistItemStatus] = mapped_column(
        enum_column(ChecklistItemStatus), default=ChecklistItemStatus.PENDING, nullable=False
    )
    evidence_notes: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    deployment_plan: Mapped[DeploymentPlan] = relationship(back_populates="checklist_items")
