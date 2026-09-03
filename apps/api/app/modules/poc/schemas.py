import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.modules.accounts.enums import StageName, StageStatus
from app.modules.poc.enums import (
    MetricOperator,
    MetricResultStatus,
    PocDecisionType,
    PocPlanStatus,
    PocReviewDecision,
)
from app.modules.solutions.schemas import SolutionProposalResponse


class PocPlanUpdate(BaseModel):
    objective: str | None = Field(default=None, min_length=3, max_length=5000)
    business_problem: str | None = Field(default=None, min_length=3, max_length=5000)
    scope: str | None = Field(default=None, min_length=3, max_length=5000)
    required_data: list[str] | None = Field(default=None, min_length=1, max_length=30)
    architecture: str | None = Field(default=None, min_length=3, max_length=5000)
    timeline_days: int | None = Field(default=None, ge=1, le=365)
    evaluation_dataset: str | None = Field(default=None, min_length=3, max_length=5000)
    expected_output: str | None = Field(default=None, min_length=3, max_length=5000)
    risks: list[str] | None = Field(default=None, min_length=1, max_length=30)

    @field_validator(
        "objective",
        "business_problem",
        "scope",
        "architecture",
        "evaluation_dataset",
        "expected_output",
    )
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("required_data", "risks")
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


class PocReviewRequest(BaseModel):
    decision: PocReviewDecision
    notes: str = Field(min_length=2, max_length=2000)

    @field_validator("notes")
    @classmethod
    def clean_notes(cls, value: str) -> str:
        return value.strip()


class PocMetricUpdate(BaseModel):
    target_operator: MetricOperator | None = None
    target_value: float | None = None
    unit: str | None = Field(default=None, min_length=1, max_length=40)
    actual_value: float | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("unit", "notes")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        return self


class PocDecisionCreate(BaseModel):
    decision: PocDecisionType
    rationale: str = Field(min_length=2, max_length=3000)

    @field_validator("rationale")
    @classmethod
    def clean_rationale(cls, value: str) -> str:
        return value.strip()


class PocMetricResponse(BaseModel):
    id: uuid.UUID
    metric_key: str
    name: str
    target_operator: MetricOperator
    target_value: float
    unit: str
    actual_value: float | None
    result_status: MetricResultStatus
    notes: str | None
    position: int
    created_at: datetime
    updated_at: datetime


class PocDecisionResponse(BaseModel):
    id: uuid.UUID
    decision: PocDecisionType
    rationale: str
    created_at: datetime


class PocPlanResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    objective: str
    business_problem: str
    scope: str
    required_data: list[str]
    architecture: str
    timeline_days: int
    evaluation_dataset: str
    expected_output: str
    risks: list[str]
    status: PocPlanStatus
    review_notes: str | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    solution_proposal: SolutionProposalResponse
    metrics: list[PocMetricResponse]
    decisions: list[PocDecisionResponse]


class PocWorkspaceResponse(BaseModel):
    account_id: uuid.UUID
    current_stage: StageName
    poc_stage_status: StageStatus
    evaluation_stage_status: StageStatus
    accepted_solution: SolutionProposalResponse | None
    plan: PocPlanResponse | None
