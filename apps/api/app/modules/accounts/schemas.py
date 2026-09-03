import re
import uuid
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.accounts.enums import ActorType, StageName, StageStatus


def normalize_website(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", value) and not value.lower().startswith(
        ("http://", "https://")
    ):
        raise ValueError("Website must use HTTP or HTTPS")
    if "://" not in value:
        value = f"https://{value}"
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Website must be a valid HTTP or HTTPS URL")
    return value


class AccountFields(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    website: str | None = Field(default=None, max_length=500)
    industry: str | None = Field(default=None, max_length=120)
    region: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=10_000)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Account name cannot be blank")
        return value

    @field_validator("website")
    @classmethod
    def clean_website(cls, value: str | None) -> str | None:
        return normalize_website(value)

    @field_validator("industry", "region", "notes")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class AccountCreate(AccountFields):
    pass


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    website: str | None = Field(default=None, max_length=500)
    industry: str | None = Field(default=None, max_length=120)
    region: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=10_000)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Account name cannot be blank")
        return value

    @model_validator(mode="after")
    def require_name_when_supplied(self):
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Account name cannot be null")
        return self

    @field_validator("website")
    @classmethod
    def clean_website(cls, value: str | None) -> str | None:
        return normalize_website(value)

    @field_validator("industry", "region", "notes")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    website: str | None
    industry: str | None
    region: str | None
    notes: str | None
    is_demo: bool
    current_stage: StageName
    archived_at: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime


class AccountListResponse(BaseModel):
    items: list[AccountResponse]
    total: int
    limit: int
    offset: int


class StageStateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stage: StageName
    status: StageStatus
    started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime


class WorkflowResponse(BaseModel):
    account_id: uuid.UUID
    current_stage: StageName
    stages: list[StageStateResponse]


class WorkflowTransitionRequest(BaseModel):
    stage: StageName
    status: StageStatus
    reason: str = Field(min_length=2, max_length=500)

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, value: str) -> str:
        return value.strip()


class ActivityResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    actor_type: ActorType
    event_type: str
    entity_type: str
    entity_id: str | None
    summary: str
    metadata: dict[str, Any]
    created_at: datetime


class ActivityListResponse(BaseModel):
    items: list[ActivityResponse]
    total: int
