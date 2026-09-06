import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.knowledge.enums import (
    AnswerProvider,
    Confidentiality,
    DocumentStatus,
    EmbeddingProvider,
    EvidenceCandidateStatus,
    KnowledgeScope,
)


class KnowledgeFilters(BaseModel):
    document_type: str | None = Field(default=None, max_length=80)
    industry: str | None = Field(default=None, max_length=120)
    region: str | None = Field(default=None, max_length=120)
    product: str | None = Field(default=None, max_length=160)
    deployment_mode: str | None = Field(default=None, max_length=120)
    confidentiality: Confidentiality | None = None

    @field_validator("document_type", "industry", "region", "product", "deployment_mode")
    @classmethod
    def clean_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=2000)
    scopes: list[KnowledgeScope] = Field(
        default_factory=lambda: [KnowledgeScope.ACCOUNT, KnowledgeScope.ENTERPRISE],
        min_length=1,
        max_length=2,
    )
    filters: KnowledgeFilters = Field(default_factory=KnowledgeFilters)
    top_k: int = Field(default=6, ge=1, le=12)

    @field_validator("query")
    @classmethod
    def clean_query(cls, value: str) -> str:
        return value.strip()


class KnowledgeAnswerRequest(KnowledgeSearchRequest):
    pass


class KnowledgeDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID | None
    knowledge_scope: KnowledgeScope
    document_type: str
    title: str
    source_file: str
    media_type: str
    size_bytes: int
    checksum_sha256: str
    status: DocumentStatus
    confidentiality: Confidentiality
    version: int
    effective_date: date | None
    industry: str | None
    region: str | None
    product: str | None
    deployment_mode: str | None
    page_count: int
    chunk_count: int
    embedding_provider: EmbeddingProvider
    embedding_model: str
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class KnowledgeCitation(BaseModel):
    citation_id: str
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    knowledge_scope: KnowledgeScope
    source_file: str
    document_title: str
    document_version: int
    page_number: int | None
    section: str | None
    chunk_position: int
    excerpt: str
    retrieval_score: float
    keyword_score: float
    vector_score: float
    rerank_score: float
    metadata: dict[str, Any]


class KnowledgeSearchResponse(BaseModel):
    account_id: uuid.UUID
    query: str
    scopes: list[KnowledgeScope]
    citations: list[KnowledgeCitation]
    candidate_count: int
    retrieval_strategy: str


class EvidenceCandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    citation_id: str
    knowledge_scope: KnowledgeScope
    source_file: str
    document_title: str
    document_version: int
    page_number: int | None
    section: str | None
    excerpt: str
    retrieval_score: float
    rerank_score: float
    metadata: dict[str, Any]
    status: EvidenceCandidateStatus
    created_at: datetime


class KnowledgeQueryResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    question: str
    answer: str
    provider: AnswerProvider
    model: str | None
    scopes: list[str]
    filters: dict[str, Any]
    retrieval_metadata: dict[str, Any]
    citations: list[EvidenceCandidateResponse]
    created_at: datetime


class KnowledgeWorkspaceResponse(BaseModel):
    account_id: uuid.UUID
    answer_provider: AnswerProvider
    live_answer_available: bool
    embedding_provider: EmbeddingProvider
    accepted_extensions: list[str]
    max_upload_mb: int
    accessible_scopes: list[KnowledgeScope]
    documents: list[KnowledgeDocumentResponse]
    recent_queries: list[KnowledgeQueryResponse]


class KnowledgeDocumentStatusRequest(BaseModel):
    status: DocumentStatus


class EvidenceCandidateReviewRequest(BaseModel):
    status: EvidenceCandidateStatus


class EvidenceBoundaryResponse(BaseModel):
    id: uuid.UUID
    status: EvidenceCandidateStatus
    boundary: str
