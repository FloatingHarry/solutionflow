import uuid
from datetime import UTC, datetime

from sqlalchemy import (
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
from app.modules.discovery.enums import HypothesisOrigin, HypothesisStatus
from app.modules.research.enums import EvidenceConfidence, ReviewDecision
from app.modules.research.models import Evidence


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


class OpportunityHypothesis(Base):
    __tablename__ = "opportunity_hypotheses"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "source_claim_id",
            name="uq_hypotheses_account_source_claim",
        ),
        Index("ix_hypotheses_account_status", "account_id", "status"),
        Index("ix_hypotheses_account_created", "account_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    source_claim_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("profile_claims.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[EvidenceConfidence] = mapped_column(
        enum_column(EvidenceConfidence), nullable=False
    )
    business_area: Mapped[str | None] = mapped_column(String(160))
    potential_impact: Mapped[str | None] = mapped_column(Text)
    status: Mapped[HypothesisStatus] = mapped_column(
        enum_column(HypothesisStatus),
        default=HypothesisStatus.NEED_VALIDATION,
        nullable=False,
    )
    origin: Mapped[HypothesisOrigin] = mapped_column(
        enum_column(HypothesisOrigin), default=HypothesisOrigin.MANUAL, nullable=False
    )
    review_notes: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    evidence_items: Mapped[list[Evidence]] = relationship(secondary="hypothesis_evidence")
    questions: Mapped[list["DiscoveryQuestion"]] = relationship(
        back_populates="hypothesis",
        cascade="all, delete-orphan",
        order_by="DiscoveryQuestion.position",
    )
    confirmed_need: Mapped["ConfirmedNeed | None"] = relationship(
        back_populates="hypothesis",
        cascade="all, delete-orphan",
        uselist=False,
    )


class HypothesisEvidence(Base):
    __tablename__ = "hypothesis_evidence"

    hypothesis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("opportunity_hypotheses.id", ondelete="CASCADE"),
        primary_key=True,
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("evidence.id", ondelete="CASCADE"), primary_key=True
    )


class DiscoveryQuestion(Base):
    __tablename__ = "discovery_questions"
    __table_args__ = (
        Index("ix_discovery_questions_account", "account_id", "created_at"),
        Index("ix_discovery_questions_hypothesis_position", "hypothesis_id", "position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    hypothesis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("opportunity_hypotheses.id", ondelete="CASCADE"),
        nullable=False,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    hypothesis: Mapped[OpportunityHypothesis] = relationship(back_populates="questions")
    answers: Mapped[list["CustomerAnswer"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="CustomerAnswer.answered_at",
    )


class CustomerAnswer(Base):
    __tablename__ = "customer_answers"
    __table_args__ = (
        Index("ix_customer_answers_account", "account_id", "answered_at"),
        Index("ix_customer_answers_question", "question_id", "answered_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("discovery_questions.id", ondelete="CASCADE"), nullable=False
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    respondent_name: Mapped[str | None] = mapped_column(String(160))
    respondent_role: Mapped[str | None] = mapped_column(String(160))
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    question: Mapped[DiscoveryQuestion] = relationship(back_populates="answers")


class ConfirmedNeed(Base):
    __tablename__ = "confirmed_needs"
    __table_args__ = (
        UniqueConstraint("hypothesis_id", name="uq_confirmed_needs_hypothesis"),
        Index("ix_confirmed_needs_account", "account_id", "confirmed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    hypothesis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("opportunity_hypotheses.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    business_impact: Mapped[str | None] = mapped_column(Text)
    success_metric: Mapped[str] = mapped_column(Text, nullable=False)
    constraints: Mapped[str | None] = mapped_column(Text)
    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    hypothesis: Mapped[OpportunityHypothesis] = relationship(back_populates="confirmed_need")
    supporting_answers: Mapped[list[CustomerAnswer]] = relationship(
        secondary="confirmed_need_answers"
    )


class ConfirmedNeedAnswer(Base):
    __tablename__ = "confirmed_need_answers"

    confirmed_need_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("confirmed_needs.id", ondelete="CASCADE"), primary_key=True
    )
    customer_answer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("customer_answers.id", ondelete="RESTRICT"), primary_key=True
    )


class DiscoveryReview(Base):
    __tablename__ = "discovery_reviews"
    __table_args__ = (Index("ix_discovery_reviews_account", "account_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    decision: Mapped[ReviewDecision] = mapped_column(enum_column(ReviewDecision), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
