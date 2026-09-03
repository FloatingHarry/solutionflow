import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.modules.accounts.enums import StageName
from app.modules.solutions.enums import (
    DeploymentOption,
    SolutionProposalStatus,
    SolutionReviewDecision,
)


def clean_required(value: str) -> str:
    return value.strip()


class SolutionMatchRequest(BaseModel):
    top_per_need: int = Field(default=3, ge=1, le=4)


class SolutionProposalCreate(BaseModel):
    solution_template_id: uuid.UUID
    need_ids: list[uuid.UUID] = Field(min_length=1, max_length=20)
    deployment_option: DeploymentOption


class SolutionProposalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=240)
    executive_summary: str | None = Field(default=None, min_length=5, max_length=5000)
    why_fit: str | None = Field(default=None, min_length=5, max_length=5000)
    architecture: str | None = Field(default=None, min_length=5, max_length=5000)
    required_data: list[str] | None = Field(default=None, max_length=30)
    model_tool_requirements: list[str] | None = Field(default=None, max_length=30)
    deployment_option: DeploymentOption | None = None
    security_considerations: list[str] | None = Field(default=None, max_length=30)
    risks: list[str] | None = Field(default=None, max_length=30)
    expected_business_impact: str | None = Field(default=None, min_length=3, max_length=5000)
    success_metrics: list[str] | None = Field(default=None, max_length=30)

    @field_validator(
        "title",
        "executive_summary",
        "why_fit",
        "architecture",
        "expected_business_impact",
    )
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator(
        "required_data",
        "model_tool_requirements",
        "security_considerations",
        "risks",
        "success_metrics",
    )
    @classmethod
    def clean_list(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("List fields must include at least one item")
        return cleaned

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        return self


class SolutionReviewRequest(BaseModel):
    decision: SolutionReviewDecision
    notes: str = Field(min_length=2, max_length=2000)

    @field_validator("notes")
    @classmethod
    def clean_notes(cls, value: str) -> str:
        return clean_required(value)


class NeedSummaryResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    business_impact: str | None
    success_metric: str
    constraints: str | None
    confirmed_at: datetime


class SolutionTemplateResponse(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    description: str
    target_pain_points: list[str]
    target_industries: list[str]
    required_data: list[str]
    architecture: str
    deployment_options: list[DeploymentOption]
    success_metrics: list[str]
    known_limitations: list[str]
    estimated_cost_model: str
    example_use_cases: list[str]
    is_simulated: bool
    version: int


class SolutionMatchResponse(BaseModel):
    id: uuid.UUID
    confirmed_need_id: uuid.UUID
    score: int
    rationale: str
    matched_terms: list[str]
    created_at: datetime
    template: SolutionTemplateResponse


class SolutionProposalResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    title: str
    executive_summary: str
    why_fit: str
    architecture: str
    required_data: list[str]
    model_tool_requirements: list[str]
    deployment_option: DeploymentOption
    security_considerations: list[str]
    risks: list[str]
    expected_business_impact: str
    success_metrics: list[str]
    status: SolutionProposalStatus
    review_notes: str | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    template: SolutionTemplateResponse
    derived_needs: list[NeedSummaryResponse]


class SolutionWorkspaceResponse(BaseModel):
    account_id: uuid.UUID
    current_stage: StageName
    discovery_approved: bool
    catalog_is_simulated: bool = True
    catalog: list[SolutionTemplateResponse]
    confirmed_needs: list[NeedSummaryResponse]
    matches: list[SolutionMatchResponse]
    proposals: list[SolutionProposalResponse]
