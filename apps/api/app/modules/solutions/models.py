import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.discovery.models import ConfirmedNeed
from app.modules.solutions.enums import DeploymentOption, SolutionProposalStatus


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


class SolutionTemplate(Base):
    __tablename__ = "solution_templates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    target_pain_points: Mapped[list[str]] = mapped_column(
        json_column(), default=list, nullable=False
    )
    target_industries: Mapped[list[str]] = mapped_column(
        json_column(), default=list, nullable=False
    )
    required_data: Mapped[list[str]] = mapped_column(json_column(), default=list, nullable=False)
    architecture: Mapped[str] = mapped_column(Text, nullable=False)
    deployment_options: Mapped[list[str]] = mapped_column(
        json_column(), default=list, nullable=False
    )
    success_metrics: Mapped[list[str]] = mapped_column(json_column(), default=list, nullable=False)
    known_limitations: Mapped[list[str]] = mapped_column(
        json_column(), default=list, nullable=False
    )
    estimated_cost_model: Mapped[str] = mapped_column(Text, nullable=False)
    example_use_cases: Mapped[list[str]] = mapped_column(
        json_column(), default=list, nullable=False
    )
    match_keywords: Mapped[list[str]] = mapped_column(json_column(), default=list, nullable=False)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class SolutionMatch(Base):
    __tablename__ = "solution_matches"
    __table_args__ = (
        UniqueConstraint(
            "confirmed_need_id",
            "solution_template_id",
            name="uq_solution_matches_need_template",
        ),
        CheckConstraint("score >= 0 AND score <= 100", name="ck_solution_matches_score"),
        Index("ix_solution_matches_account_score", "account_id", "score"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    confirmed_need_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("confirmed_needs.id", ondelete="CASCADE"), nullable=False
    )
    solution_template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("solution_templates.id", ondelete="RESTRICT"), nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    matched_terms: Mapped[list[str]] = mapped_column(json_column(), default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    confirmed_need: Mapped[ConfirmedNeed] = relationship()
    solution_template: Mapped[SolutionTemplate] = relationship()


class SolutionProposalNeed(Base):
    __tablename__ = "solution_proposal_needs"

    solution_proposal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("solution_proposals.id", ondelete="CASCADE"), primary_key=True
    )
    confirmed_need_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("confirmed_needs.id", ondelete="RESTRICT"), primary_key=True
    )


class SolutionProposal(Base):
    __tablename__ = "solution_proposals"
    __table_args__ = (
        Index("ix_solution_proposals_account_status", "account_id", "status"),
        Index("ix_solution_proposals_account_created", "account_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    solution_template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("solution_templates.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    why_fit: Mapped[str] = mapped_column(Text, nullable=False)
    architecture: Mapped[str] = mapped_column(Text, nullable=False)
    required_data: Mapped[list[str]] = mapped_column(json_column(), default=list, nullable=False)
    model_tool_requirements: Mapped[list[str]] = mapped_column(
        json_column(), default=list, nullable=False
    )
    deployment_option: Mapped[DeploymentOption] = mapped_column(
        enum_column(DeploymentOption), nullable=False
    )
    security_considerations: Mapped[list[str]] = mapped_column(
        json_column(), default=list, nullable=False
    )
    risks: Mapped[list[str]] = mapped_column(json_column(), default=list, nullable=False)
    expected_business_impact: Mapped[str] = mapped_column(Text, nullable=False)
    success_metrics: Mapped[list[str]] = mapped_column(json_column(), default=list, nullable=False)
    status: Mapped[SolutionProposalStatus] = mapped_column(
        enum_column(SolutionProposalStatus),
        default=SolutionProposalStatus.DRAFT,
        nullable=False,
    )
    review_notes: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    solution_template: Mapped[SolutionTemplate] = relationship()
    derived_needs: Mapped[list[ConfirmedNeed]] = relationship(secondary="solution_proposal_needs")
