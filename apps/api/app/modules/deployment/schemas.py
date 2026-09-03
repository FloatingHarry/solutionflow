import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.modules.accounts.enums import StageName, StageStatus
from app.modules.deployment.enums import ChecklistItemStatus, DeploymentPlanStatus
from app.modules.solutions.enums import DeploymentOption


def clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


class DeploymentPlanUpdate(BaseModel):
    owner: str | None = Field(default=None, min_length=2, max_length=200)
    target_launch_date: date | None = None
    rollout_strategy: str | None = Field(default=None, min_length=5, max_length=5000)
    integration_plan: str | None = Field(default=None, min_length=5, max_length=5000)
    data_governance_plan: str | None = Field(default=None, min_length=5, max_length=5000)
    monitoring_plan: str | None = Field(default=None, min_length=5, max_length=5000)
    rollback_plan: str | None = Field(default=None, min_length=5, max_length=5000)
    support_model: str | None = Field(default=None, min_length=5, max_length=5000)

    @field_validator(
        "owner",
        "rollout_strategy",
        "integration_plan",
        "data_governance_plan",
        "monitoring_plan",
        "rollback_plan",
        "support_model",
    )
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        return clean_optional(value)

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        return self


class DeploymentChecklistUpdate(BaseModel):
    owner: str | None = Field(default=None, max_length=200)
    status: ChecklistItemStatus | None = None
    evidence_notes: str | None = Field(default=None, max_length=5000)

    @field_validator("owner", "evidence_notes")
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        return clean_optional(value)

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        return self


class DeploymentCompleteRequest(BaseModel):
    notes: str = Field(min_length=2, max_length=3000)

    @field_validator("notes")
    @classmethod
    def clean_notes(cls, value: str) -> str:
        return value.strip()


class DeploymentChecklistResponse(BaseModel):
    id: uuid.UUID
    category: str
    title: str
    owner: str | None
    status: ChecklistItemStatus
    evidence_notes: str | None
    position: int
    completed_at: datetime | None
    updated_at: datetime


class DeploymentPlanResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    business_case_id: uuid.UUID
    environment: DeploymentOption
    owner: str
    target_launch_date: date | None
    rollout_strategy: str
    integration_plan: str
    data_governance_plan: str
    monitoring_plan: str
    rollback_plan: str
    support_model: str
    status: DeploymentPlanStatus
    readiness_score: int
    completion_notes: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    checklist_items: list[DeploymentChecklistResponse]


class DeploymentWorkspaceResponse(BaseModel):
    account_id: uuid.UUID
    current_stage: StageName
    deployment_stage_status: StageStatus
    business_case_approved: bool
    recommended_environment: DeploymentOption | None
    plan: DeploymentPlanResponse | None
