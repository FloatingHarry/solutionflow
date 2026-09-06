import uuid
from datetime import UTC, date, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
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
from app.modules.knowledge.enums import (
    AnswerProvider,
    Confidentiality,
    DocumentStatus,
    EmbeddingProvider,
    EvidenceCandidateStatus,
    KnowledgeScope,
)

EMBEDDING_DIMENSIONS = 384


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


def embedding_column():
    return JSON().with_variant(Vector(EMBEDDING_DIMENSIONS), "postgresql")


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    __table_args__ = (
        CheckConstraint(
            "(knowledge_scope = 'account' AND account_id IS NOT NULL) OR "
            "(knowledge_scope = 'enterprise' AND account_id IS NULL)",
            name="ck_knowledge_documents_scope_owner",
        ),
        UniqueConstraint(
            "account_id",
            "knowledge_scope",
            "source_file",
            "version",
            name="uq_knowledge_document_version",
        ),
        Index("ix_knowledge_documents_scope_status", "knowledge_scope", "status"),
        Index("ix_knowledge_documents_account_status", "account_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    knowledge_scope: Mapped[KnowledgeScope] = mapped_column(
        enum_column(KnowledgeScope), nullable=False
    )
    document_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    source_file: Mapped[str] = mapped_column(String(500), nullable=False)
    media_type: Mapped[str] = mapped_column(String(160), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[DocumentStatus] = mapped_column(
        enum_column(DocumentStatus), default=DocumentStatus.ACTIVE, nullable=False
    )
    confidentiality: Mapped[Confidentiality] = mapped_column(
        enum_column(Confidentiality), default=Confidentiality.INTERNAL, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_date: Mapped[date | None] = mapped_column(Date)
    industry: Mapped[str | None] = mapped_column(String(120), index=True)
    region: Mapped[str | None] = mapped_column(String(120), index=True)
    product: Mapped[str | None] = mapped_column(String(160), index=True)
    deployment_mode: Mapped[str | None] = mapped_column(String(120), index=True)
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedding_provider: Mapped[EmbeddingProvider] = mapped_column(
        enum_column(EmbeddingProvider), nullable=False
    )
    embedding_model: Mapped[str] = mapped_column(String(160), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(
        "metadata", json_column(), default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "position", name="uq_knowledge_chunk_position"),
        CheckConstraint(
            "(knowledge_scope = 'account' AND account_id IS NOT NULL) OR "
            "(knowledge_scope = 'enterprise' AND account_id IS NULL)",
            name="ck_knowledge_chunks_scope_owner",
        ),
        Index("ix_knowledge_chunks_account_scope", "account_id", "knowledge_scope"),
        Index("ix_knowledge_chunks_document", "document_id", "position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    knowledge_scope: Mapped[KnowledgeScope] = mapped_column(
        enum_column(KnowledgeScope), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)
    section: Mapped[str | None] = mapped_column(String(300))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    search_text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(embedding_column(), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(
        "metadata", json_column(), default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    document: Mapped[KnowledgeDocument] = relationship(back_populates="chunks")


class KnowledgeQuery(Base):
    __tablename__ = "knowledge_queries"
    __table_args__ = (Index("ix_knowledge_queries_account_created", "account_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[AnswerProvider] = mapped_column(enum_column(AnswerProvider), nullable=False)
    model: Mapped[str | None] = mapped_column(String(160))
    scopes: Mapped[list[str]] = mapped_column(json_column(), default=list, nullable=False)
    filters: Mapped[dict[str, Any]] = mapped_column(json_column(), default=dict, nullable=False)
    retrieval_metadata: Mapped[dict[str, Any]] = mapped_column(
        json_column(), default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    candidates: Mapped[list["KnowledgeEvidenceCandidate"]] = relationship(
        back_populates="query", cascade="all, delete-orphan"
    )


class KnowledgeEvidenceCandidate(Base):
    __tablename__ = "knowledge_evidence_candidates"
    __table_args__ = (
        UniqueConstraint("query_id", "citation_id", name="uq_knowledge_candidate_citation"),
        Index("ix_knowledge_candidates_account_created", "account_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    query_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("knowledge_queries.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("knowledge_chunks.id", ondelete="SET NULL")
    )
    citation_id: Mapped[str] = mapped_column(String(80), nullable=False)
    knowledge_scope: Mapped[KnowledgeScope] = mapped_column(
        enum_column(KnowledgeScope), nullable=False
    )
    source_file: Mapped[str] = mapped_column(String(500), nullable=False)
    document_title: Mapped[str] = mapped_column(String(240), nullable=False)
    document_version: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)
    section: Mapped[str | None] = mapped_column(String(300))
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    retrieval_score: Mapped[float] = mapped_column(Float, nullable=False)
    rerank_score: Mapped[float] = mapped_column(Float, nullable=False)
    metadata_snapshot: Mapped[dict[str, Any]] = mapped_column(
        "metadata", json_column(), default=dict, nullable=False
    )
    status: Mapped[EvidenceCandidateStatus] = mapped_column(
        enum_column(EvidenceCandidateStatus),
        default=EvidenceCandidateStatus.RETRIEVED,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    query: Mapped[KnowledgeQuery] = relationship(back_populates="candidates")
