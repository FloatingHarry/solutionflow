import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.modules.accounts.enums import StageName, StageStatus
from app.modules.business_case.enums import (
    AssessmentRating,
    BusinessCaseReviewDecision,
    BusinessCaseStatus,
)
from app.modules.poc.schemas import PocPlanResponse
from app.modules.solutions.enums import DeploymentOption

CurrencyCode = Literal["EUR", "USD", "GBP", "CNY"]


class RoiScenarioUpdate(BaseModel):
    currency: CurrencyCode | None = None
    number_employees: int | None = Field(default=None, ge=1, le=1_000_000)
    average_hourly_cost: float | None = Field(default=None, ge=0, le=1_000_000)
    current_time_per_task_minutes: float | None = Field(default=None, gt=0, le=100_000)
    tasks_per_employee_per_month: float | None = Field(default=None, gt=0, le=1_000_000)
    expected_time_reduction_percent: float | None = Field(default=None, ge=0, le=100)
    monthly_ai_cost: float | None = Field(default=None, ge=0, le=1_000_000_000)
    implementation_cost: float | None = Field(default=None, ge=0, le=1_000_000_000)

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        return self


class DeploymentRecommendationUpdate(BaseModel):
    recommended_deployment: DeploymentOption | None = None
    deployment_rationale: str | None = Field(default=None, min_length=3, max_length=5000)
    assumptions: list[str] | None = Field(default=None, min_length=1, max_length=30)

    @field_validator("deployment_rationale")
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("assumptions")
    @classmethod
    def clean_list(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("Assumptions must include at least one item")
        return cleaned

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        return self


class AccountBriefUpdate(BaseModel):
    executive_summary: str | None = Field(default=None, min_length=5, max_length=8000)
    customer_context: str | None = Field(default=None, min_length=5, max_length=8000)
    confirmed_needs_summary: str | None = Field(default=None, min_length=5, max_length=8000)
    solution_summary: str | None = Field(default=None, min_length=5, max_length=8000)
    poc_summary: str | None = Field(default=None, min_length=5, max_length=8000)
    roi_summary: str | None = Field(default=None, min_length=5, max_length=8000)
    deployment_summary: str | None = Field(default=None, min_length=5, max_length=8000)
    key_risks: list[str] | None = Field(default=None, min_length=1, max_length=30)
    next_steps: list[str] | None = Field(default=None, min_length=1, max_length=30)

    @field_validator(
        "executive_summary",
        "customer_context",
        "confirmed_needs_summary",
        "solution_summary",
        "poc_summary",
        "roi_summary",
        "deployment_summary",
    )
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("key_risks", "next_steps")
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


class BusinessCaseReviewRequest(BaseModel):
    decision: BusinessCaseReviewDecision
    notes: str = Field(min_length=2, max_length=3000)

    @field_validator("notes")
    @classmethod
    def clean_notes(cls, value: str) -> str:
        return value.strip()


class DeploymentAssessmentResponse(BaseModel):
    id: uuid.UUID
    option: DeploymentOption
    cost: AssessmentRating
    implementation_difficulty: AssessmentRating
    data_privacy: AssessmentRating
    scalability: AssessmentRating
    maintenance: AssessmentRating
    latency: AssessmentRating
    compliance: AssessmentRating
    notes: list[str]
    position: int


class AccountBriefResponse(BaseModel):
    id: uuid.UUID
    executive_summary: str
    customer_context: str
    confirmed_needs_summary: str
    solution_summary: str
    poc_summary: str
    roi_summary: str
    deployment_summary: str
    key_risks: list[str]
    next_steps: list[str]
    created_at: datetime
    updated_at: datetime


class BusinessCaseResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    currency: CurrencyCode
    number_employees: int
    average_hourly_cost: float
    current_time_per_task_minutes: float
    tasks_per_employee_per_month: float
    expected_time_reduction_percent: float
    monthly_ai_cost: float
    implementation_cost: float
    current_monthly_cost: float
    estimated_new_labor_cost: float
    estimated_new_total_cost: float
    monthly_savings: float
    annual_savings: float
    estimated_first_year_roi_percent: float | None
    payback_period_months: float | None
    recommended_deployment: DeploymentOption
    deployment_rationale: str
    assumptions: list[str]
    scenario_is_estimate: bool = True
    status: BusinessCaseStatus
    review_notes: str | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deployment_assessments: list[DeploymentAssessmentResponse]
    brief: AccountBriefResponse
    poc_plan: PocPlanResponse


class BusinessCaseWorkspaceResponse(BaseModel):
    account_id: uuid.UUID
    current_stage: StageName
    business_case_stage_status: StageStatus
    deployment_stage_status: StageStatus
    evaluation_completed: bool
    case: BusinessCaseResponse | None
