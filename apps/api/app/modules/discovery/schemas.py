import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.accounts.enums import StageName
from app.modules.discovery.enums import (
    HypothesisOrigin,
    HypothesisReviewDecision,
    HypothesisStatus,
)
from app.modules.research.enums import EvidenceConfidence, ReviewDecision
from app.modules.research.schemas import CitationResponse


def clean_required(value: str) -> str:
    return value.strip()


def clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


class DiscoveryGenerateRequest(BaseModel):
    max_hypotheses: int = Field(default=3, ge=1, le=5)


class HypothesisCreate(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    description: str = Field(min_length=5, max_length=5000)
    confidence: EvidenceConfidence = EvidenceConfidence.MEDIUM
    business_area: str | None = Field(default=None, max_length=160)
    potential_impact: str | None = Field(default=None, max_length=3000)
    evidence_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)

    @field_validator("title", "description")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        return clean_required(value)

    @field_validator("business_area", "potential_impact")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        return clean_optional(value)


class HypothesisReviewRequest(BaseModel):
    decision: HypothesisReviewDecision
    notes: str = Field(min_length=2, max_length=2000)

    @field_validator("notes")
    @classmethod
    def clean_notes(cls, value: str) -> str:
        return clean_required(value)


class DiscoveryQuestionCreate(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    rationale: str | None = Field(default=None, max_length=2000)

    @field_validator("question")
    @classmethod
    def clean_question(cls, value: str) -> str:
        return clean_required(value)

    @field_validator("rationale")
    @classmethod
    def clean_rationale(cls, value: str | None) -> str | None:
        return clean_optional(value)


class DiscoveryQuestionUpdate(BaseModel):
    question: str | None = Field(default=None, min_length=3, max_length=2000)
    rationale: str | None = Field(default=None, max_length=2000)

    @field_validator("question")
    @classmethod
    def clean_question(cls, value: str | None) -> str | None:
        return clean_optional(value)

    @field_validator("rationale")
    @classmethod
    def clean_rationale(cls, value: str | None) -> str | None:
        return clean_optional(value)

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        return self


class CustomerAnswerCreate(BaseModel):
    answer_text: str = Field(min_length=2, max_length=10_000)
    respondent_name: str | None = Field(default=None, max_length=160)
    respondent_role: str | None = Field(default=None, max_length=160)

    @field_validator("answer_text")
    @classmethod
    def clean_answer(cls, value: str) -> str:
        return clean_required(value)

    @field_validator("respondent_name", "respondent_role")
    @classmethod
    def clean_respondent(cls, value: str | None) -> str | None:
        return clean_optional(value)


class CustomerAnswerUpdate(BaseModel):
    answer_text: str | None = Field(default=None, min_length=2, max_length=10_000)
    respondent_name: str | None = Field(default=None, max_length=160)
    respondent_role: str | None = Field(default=None, max_length=160)

    @field_validator("answer_text", "respondent_name", "respondent_role")
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        return clean_optional(value)

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        return self


class ConfirmedNeedCreate(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    description: str = Field(min_length=5, max_length=5000)
    business_impact: str | None = Field(default=None, max_length=5000)
    success_metric: str = Field(min_length=3, max_length=3000)
    constraints: str | None = Field(default=None, max_length=5000)
    answer_ids: list[uuid.UUID] = Field(default_factory=list, max_length=50)

    @field_validator("title", "description", "success_metric")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        return clean_required(value)

    @field_validator("business_impact", "constraints")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        return clean_optional(value)


class DiscoveryReviewRequest(BaseModel):
    decision: ReviewDecision
    notes: str = Field(min_length=2, max_length=2000)

    @field_validator("notes")
    @classmethod
    def clean_notes(cls, value: str) -> str:
        return clean_required(value)


class CustomerAnswerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    question_id: uuid.UUID
    answer_text: str
    respondent_name: str | None
    respondent_role: str | None
    answered_at: datetime
    created_at: datetime
    updated_at: datetime


class DiscoveryQuestionResponse(BaseModel):
    id: uuid.UUID
    hypothesis_id: uuid.UUID
    question: str
    rationale: str | None
    position: int
    created_at: datetime
    updated_at: datetime
    answers: list[CustomerAnswerResponse]


class ConfirmedNeedResponse(BaseModel):
    id: uuid.UUID
    hypothesis_id: uuid.UUID
    title: str
    description: str
    business_impact: str | None
    success_metric: str
    constraints: str | None
    confirmed_at: datetime
    supporting_answer_ids: list[uuid.UUID]


class OpportunityHypothesisResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    source_claim_id: uuid.UUID | None
    title: str
    description: str
    confidence: EvidenceConfidence
    business_area: str | None
    potential_impact: str | None
    status: HypothesisStatus
    origin: HypothesisOrigin
    review_notes: str | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    evidence: list[CitationResponse]
    questions: list[DiscoveryQuestionResponse]
    confirmed_need: ConfirmedNeedResponse | None


class DiscoveryReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    decision: ReviewDecision
    notes: str
    created_at: datetime


class DiscoveryWorkspaceResponse(BaseModel):
    account_id: uuid.UUID
    current_stage: StageName
    research_approved: bool
    hypotheses: list[OpportunityHypothesisResponse]
    confirmed_needs: list[ConfirmedNeedResponse]
    reviews: list[DiscoveryReviewResponse]
