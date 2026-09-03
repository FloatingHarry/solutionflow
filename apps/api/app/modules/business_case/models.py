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
from app.modules.business_case.enums import AssessmentRating, BusinessCaseStatus
from app.modules.poc.models import PocPlan
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


def json_column() -> JSON:
    return JSON().with_variant(JSONB, "postgresql")


class BusinessCase(Base):
    __tablename__ = "business_cases"
    __table_args__ = (
        UniqueConstraint("poc_plan_id", name="uq_business_cases_poc_plan"),
        Index("ix_business_cases_account_status", "account_id", "status"),
        CheckConstraint("number_employees > 0", name="ck_business_cases_employees_positive"),
        CheckConstraint("average_hourly_cost >= 0", name="ck_business_cases_hourly_cost"),
        CheckConstraint(
            "current_time_per_task_minutes > 0", name="ck_business_cases_task_time_positive"
        ),
        CheckConstraint(
            "tasks_per_employee_per_month > 0", name="ck_business_cases_tasks_positive"
        ),
        CheckConstraint(
            "expected_time_reduction_percent >= 0 AND "
            "expected_time_reduction_percent <= 100",
            name="ck_business_cases_reduction_range",
        ),
        CheckConstraint("monthly_ai_cost >= 0", name="ck_business_cases_ai_cost"),
        CheckConstraint("implementation_cost >= 0", name="ck_business_cases_implementation"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    poc_plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("poc_plans.id", ondelete="RESTRICT"), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    number_employees: Mapped[int] = mapped_column(Integer, nullable=False)
    average_hourly_cost: Mapped[float] = mapped_column(Float, nullable=False)
    current_time_per_task_minutes: Mapped[float] = mapped_column(Float, nullable=False)
    tasks_per_employee_per_month: Mapped[float] = mapped_column(Float, nullable=False)
    expected_time_reduction_percent: Mapped[float] = mapped_column(Float, nullable=False)
    monthly_ai_cost: Mapped[float] = mapped_column(Float, nullable=False)
    implementation_cost: Mapped[float] = mapped_column(Float, nullable=False)
    current_monthly_cost: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_new_labor_cost: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_new_total_cost: Mapped[float] = mapped_column(Float, nullable=False)
    monthly_savings: Mapped[float] = mapped_column(Float, nullable=False)
    annual_savings: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_first_year_roi_percent: Mapped[float | None] = mapped_column(Float)
    payback_period_months: Mapped[float | None] = mapped_column(Float)
    recommended_deployment: Mapped[DeploymentOption] = mapped_column(
        enum_column(DeploymentOption), nullable=False
    )
    deployment_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    assumptions: Mapped[list[str]] = mapped_column(json_column(), default=list, nullable=False)
    status: Mapped[BusinessCaseStatus] = mapped_column(
        enum_column(BusinessCaseStatus), default=BusinessCaseStatus.DRAFT, nullable=False
    )
    review_notes: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    poc_plan: Mapped[PocPlan] = relationship()
    deployment_assessments: Mapped[list["DeploymentAssessment"]] = relationship(
        back_populates="business_case",
        cascade="all, delete-orphan",
        order_by="DeploymentAssessment.position",
    )
    brief: Mapped["AccountBrief"] = relationship(
        back_populates="business_case",
        cascade="all, delete-orphan",
        uselist=False,
    )


class DeploymentAssessment(Base):
    __tablename__ = "deployment_assessments"
    __table_args__ = (
        UniqueConstraint(
            "business_case_id", "option", name="uq_deployment_assessments_case_option"
        ),
        CheckConstraint("position >= 0", name="ck_deployment_assessments_position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    business_case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("business_cases.id", ondelete="CASCADE"), nullable=False
    )
    option: Mapped[DeploymentOption] = mapped_column(enum_column(DeploymentOption), nullable=False)
    cost: Mapped[AssessmentRating] = mapped_column(enum_column(AssessmentRating), nullable=False)
    implementation_difficulty: Mapped[AssessmentRating] = mapped_column(
        enum_column(AssessmentRating), nullable=False
    )
    data_privacy: Mapped[AssessmentRating] = mapped_column(
        enum_column(AssessmentRating), nullable=False
    )
    scalability: Mapped[AssessmentRating] = mapped_column(
        enum_column(AssessmentRating), nullable=False
    )
    maintenance: Mapped[AssessmentRating] = mapped_column(
        enum_column(AssessmentRating), nullable=False
    )
    latency: Mapped[AssessmentRating] = mapped_column(enum_column(AssessmentRating), nullable=False)
    compliance: Mapped[AssessmentRating] = mapped_column(
        enum_column(AssessmentRating), nullable=False
    )
    notes: Mapped[list[str]] = mapped_column(json_column(), default=list, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    business_case: Mapped[BusinessCase] = relationship(back_populates="deployment_assessments")


class AccountBrief(Base):
    __tablename__ = "account_briefs"
    __table_args__ = (UniqueConstraint("business_case_id", name="uq_account_briefs_case"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    business_case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("business_cases.id", ondelete="CASCADE"), nullable=False
    )
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    customer_context: Mapped[str] = mapped_column(Text, nullable=False)
    confirmed_needs_summary: Mapped[str] = mapped_column(Text, nullable=False)
    solution_summary: Mapped[str] = mapped_column(Text, nullable=False)
    poc_summary: Mapped[str] = mapped_column(Text, nullable=False)
    roi_summary: Mapped[str] = mapped_column(Text, nullable=False)
    deployment_summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_risks: Mapped[list[str]] = mapped_column(json_column(), default=list, nullable=False)
    next_steps: Mapped[list[str]] = mapped_column(json_column(), default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    business_case: Mapped[BusinessCase] = relationship(back_populates="brief")
