import uuid
from datetime import datetime

from pydantic import BaseModel

from app.modules.accounts.enums import StageName, StageStatus
from app.modules.deployment.enums import DeploymentPlanStatus


class EvaluationTaskResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    category: str
    label: str
    expected: str
    actual: str
    passed: bool
    score: float
    latency_ms: float
    estimated_cost_usd: float
    notes: str
    position: int


class EvaluationMetricSummary(BaseModel):
    category: str
    label: str
    passed: int
    total: int
    score: float


class SystemEvaluationRunResponse(BaseModel):
    id: uuid.UUID
    name: str
    methodology: str
    dataset_version: str
    is_deterministic: bool
    demo_account_count: int
    total_tasks: int
    passed_tasks: int
    pass_rate: float
    hallucination_rate: float
    citation_correctness: float
    task_completion_rate: float
    mean_latency_ms: float
    estimated_cost_usd: float
    created_at: datetime
    completed_at: datetime
    metrics: list[EvaluationMetricSummary]
    tasks: list[EvaluationTaskResponse]


class DemoAccountSummary(BaseModel):
    id: uuid.UUID
    name: str
    industry: str | None
    region: str | None
    current_stage: StageName
    deployment_status: StageStatus
    deployment_plan_status: DeploymentPlanStatus | None
    workflow_completion: int


class SystemEvaluationWorkspaceResponse(BaseModel):
    required_demo_accounts: int = 5
    required_task_minimum: int = 30
    methodology_note: str
    demo_accounts: list[DemoAccountSummary]
    latest_run: SystemEvaluationRunResponse | None
