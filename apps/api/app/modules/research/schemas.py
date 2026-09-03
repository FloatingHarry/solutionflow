import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.research.enums import (
    ClaimReviewStatus,
    EvidenceConfidence,
    EvidenceVerification,
    ProfileSection,
    ResearchProviderName,
    ResearchStatus,
    ReviewDecision,
    SourceType,
)


class ResearchRunCreate(BaseModel):
    provider: ResearchProviderName | None = None


class ResearchReviewRequest(BaseModel):
    decision: ReviewDecision
    notes: str = Field(min_length=2, max_length=2000)

    @field_validator("notes")
    @classmethod
    def clean_notes(cls, value: str) -> str:
        return value.strip()


class ResearchRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    retry_of_id: uuid.UUID | None
    status: ResearchStatus
    provider: ResearchProviderName
    provider_response_id: str | None
    query_plan: dict[str, Any]
    error_message: str | None
    review_notes: str | None
    started_at: datetime | None
    finished_at: datetime | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SourceResponse(BaseModel):
    id: uuid.UUID
    source_type: SourceType
    title: str
    url: str | None
    publisher: str | None
    published_at: date | None
    retrieved_at: datetime
    content_excerpt: str | None
    is_official: bool
    metadata: dict[str, Any]


class CitationResponse(BaseModel):
    evidence_id: uuid.UUID
    source_id: uuid.UUID
    source_title: str
    source_url: str | None
    publisher: str | None
    supporting_text: str
    locator: str | None
    confidence: EvidenceConfidence
    verification_status: EvidenceVerification
    retrieved_at: datetime


class ProfileClaimResponse(BaseModel):
    id: uuid.UUID
    section: ProfileSection
    statement: str
    confidence: EvidenceConfidence
    is_inference: bool
    review_status: ClaimReviewStatus
    citations: list[CitationResponse]


class CompanyProfileResponse(BaseModel):
    id: uuid.UUID
    research_run_id: uuid.UUID
    summary: str
    is_simulated: bool
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    claims: list[ProfileClaimResponse]


class ResearchWorkspaceResponse(BaseModel):
    account_id: uuid.UUID
    configured_provider: ResearchProviderName
    live_research_available: bool
    latest_run: ResearchRunResponse | None
    run_history: list[ResearchRunResponse]
    profile: CompanyProfileResponse | None
    sources: list[SourceResponse]
