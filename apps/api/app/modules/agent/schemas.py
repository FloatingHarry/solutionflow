import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.modules.agent.enums import AgentActionStatus, AgentProvider, AgentRunStatus


class AgentRunCreate(BaseModel):
    goal: str = Field(min_length=3, max_length=2000)

    @field_validator("goal")
    @classmethod
    def clean_goal(cls, value: str) -> str:
        return value.strip()


class AgentActionDecision(BaseModel):
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("note")
    @classmethod
    def clean_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class AgentActionResponse(BaseModel):
    key: str
    title: str
    description: str
    reason: str
    target_path: str | None
    requires_approval: bool
    status: AgentActionStatus
    result: dict[str, Any]


class AgentRunResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    goal: str
    status: AgentRunStatus
    provider: AgentProvider
    model: str | None
    provider_response_id: str | None
    stage_snapshot: str
    summary: str
    observations: list[str]
    plan: list[str]
    question: str | None
    trace: list[dict[str, Any]]
    action: AgentActionResponse | None
    approval_note: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class AgentWorkspaceResponse(BaseModel):
    account_id: uuid.UUID
    live_agent_available: bool
    mode: AgentProvider
    model: str | None
    capabilities: list[str]
    starter_prompts: list[str]
    runs: list[AgentRunResponse]
