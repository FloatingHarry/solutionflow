from fastapi import APIRouter, status

from app.db.session import SessionDep
from app.modules.evaluation import service
from app.modules.evaluation.models import SystemEvaluationRun, SystemEvaluationTask
from app.modules.evaluation.schemas import (
    DemoAccountSummary,
    EvaluationMetricSummary,
    EvaluationTaskResponse,
    SystemEvaluationRunResponse,
    SystemEvaluationWorkspaceResponse,
)

router = APIRouter(tags=["system-evaluation"])


def serialize_task(task: SystemEvaluationTask) -> EvaluationTaskResponse:
    return EvaluationTaskResponse(
        id=task.id,
        account_id=task.account_id,
        category=task.category,
        label=task.label,
        expected=task.expected,
        actual=task.actual,
        passed=task.passed,
        score=task.score,
        latency_ms=task.latency_ms,
        estimated_cost_usd=task.estimated_cost_usd,
        notes=task.notes,
        position=task.position,
    )


def serialize_run(run: SystemEvaluationRun) -> SystemEvaluationRunResponse:
    return SystemEvaluationRunResponse(
        id=run.id,
        name=run.name,
        methodology=run.methodology,
        dataset_version=run.dataset_version,
        is_deterministic=run.is_deterministic,
        demo_account_count=run.demo_account_count,
        total_tasks=run.total_tasks,
        passed_tasks=run.passed_tasks,
        pass_rate=run.pass_rate,
        hallucination_rate=run.hallucination_rate,
        citation_correctness=run.citation_correctness,
        task_completion_rate=run.task_completion_rate,
        mean_latency_ms=run.mean_latency_ms,
        estimated_cost_usd=run.estimated_cost_usd,
        created_at=run.created_at,
        completed_at=run.completed_at,
        metrics=[EvaluationMetricSummary(**item) for item in service.metric_summaries(run)],
        tasks=[serialize_task(task) for task in run.tasks],
    )


def workspace_response(session: SessionDep) -> SystemEvaluationWorkspaceResponse:
    latest = service.latest_run(session)
    return SystemEvaluationWorkspaceResponse(
        methodology_note=service.METHODOLOGY,
        demo_accounts=[
            DemoAccountSummary(**item) for item in service.list_demo_summaries(session)
        ],
        latest_run=serialize_run(latest) if latest else None,
    )


@router.get("/system-evaluation", response_model=SystemEvaluationWorkspaceResponse)
def get_system_evaluation(session: SessionDep) -> SystemEvaluationWorkspaceResponse:
    return workspace_response(session)


@router.post(
    "/demo-accounts/seed",
    response_model=SystemEvaluationWorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_demo_accounts(session: SessionDep) -> SystemEvaluationWorkspaceResponse:
    service.seed_demo_accounts(session)
    return workspace_response(session)


@router.post(
    "/system-evaluations/run",
    response_model=SystemEvaluationWorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_system_evaluation(session: SessionDep) -> SystemEvaluationWorkspaceResponse:
    service.run_system_evaluation(session)
    return workspace_response(session)
