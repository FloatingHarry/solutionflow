import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.research.enums import (
    ClaimReviewStatus,
    EvidenceConfidence,
    EvidenceVerification,
    ProfileSection,
    ResearchProviderName,
    ResearchStatus,
    SourceType,
)


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


class ResearchRun(Base):
    __tablename__ = "research_runs"
    __table_args__ = (
        Index("ix_research_runs_account_created", "account_id", "created_at"),
        Index("ix_research_runs_account_status", "account_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    retry_of_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("research_runs.id", ondelete="SET NULL")
    )
    status: Mapped[ResearchStatus] = mapped_column(
        enum_column(ResearchStatus), default=ResearchStatus.QUEUED, nullable=False
    )
    provider: Mapped[ResearchProviderName] = mapped_column(
        enum_column(ResearchProviderName), nullable=False
    )
    provider_response_id: Mapped[str | None] = mapped_column(String(120))
    query_plan: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=dict, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    review_notes: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    profile: Mapped["CompanyProfile | None"] = relationship(
        back_populates="research_run", cascade="all, delete-orphan", uselist=False
    )
    sources: Mapped[list["Source"]] = relationship(
        back_populates="research_run", cascade="all, delete-orphan"
    )


class Source(Base):
    __tablename__ = "sources"
    __table_args__ = (
        Index("ix_sources_account_retrieved", "account_id", "retrieved_at"),
        Index("ix_sources_run_url", "research_run_id", "url"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    research_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[SourceType] = mapped_column(enum_column(SourceType), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str | None] = mapped_column(String(2000))
    publisher: Mapped[str | None] = mapped_column(String(300))
    published_at: Mapped[date | None] = mapped_column(Date)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    content_excerpt: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    is_official: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON().with_variant(JSONB, "postgresql"), default=dict, nullable=False
    )

    research_run: Mapped[ResearchRun] = relationship(back_populates="sources")
    evidence_items: Mapped[list["Evidence"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class Evidence(Base):
    __tablename__ = "evidence"
    __table_args__ = (Index("ix_evidence_account_created", "account_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    research_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
    )
    supporting_text: Mapped[str] = mapped_column(Text, nullable=False)
    locator: Mapped[str | None] = mapped_column(String(500))
    confidence: Mapped[EvidenceConfidence] = mapped_column(
        enum_column(EvidenceConfidence), nullable=False
    )
    verification_status: Mapped[EvidenceVerification] = mapped_column(
        enum_column(EvidenceVerification), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    source: Mapped[Source] = relationship(back_populates="evidence_items")
    claims: Mapped[list["ProfileClaim"]] = relationship(
        secondary="claim_evidence", back_populates="evidence_items"
    )


class CompanyProfile(Base):
    __tablename__ = "company_profiles"
    __table_args__ = (
        UniqueConstraint("research_run_id", name="uq_company_profiles_research_run"),
        Index("ix_company_profiles_account_created", "account_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    research_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    research_run: Mapped[ResearchRun] = relationship(back_populates="profile")
    claims: Mapped[list["ProfileClaim"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="ProfileClaim.position",
    )


class ProfileClaim(Base):
    __tablename__ = "profile_claims"
    __table_args__ = (Index("ix_profile_claims_profile_section", "profile_id", "section"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("company_profiles.id", ondelete="CASCADE"), nullable=False
    )
    section: Mapped[ProfileSection] = mapped_column(enum_column(ProfileSection), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[EvidenceConfidence] = mapped_column(
        enum_column(EvidenceConfidence), nullable=False
    )
    is_inference: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    review_status: Mapped[ClaimReviewStatus] = mapped_column(
        enum_column(ClaimReviewStatus), default=ClaimReviewStatus.AI_GENERATED, nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    profile: Mapped[CompanyProfile] = relationship(back_populates="claims")
    evidence_items: Mapped[list[Evidence]] = relationship(
        secondary="claim_evidence", back_populates="claims"
    )


class ClaimEvidence(Base):
    __tablename__ = "claim_evidence"

    claim_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profile_claims.id", ondelete="CASCADE"), primary_key=True
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("evidence.id", ondelete="CASCADE"), primary_key=True
    )
