import uuid

from fastapi import APIRouter, HTTPException, status

from app.db.session import SessionDep
from app.modules.accounts import service as accounts_service
from app.modules.poc import service
from app.modules.poc.models import PocDecision, PocMetric, PocPlan
from app.modules.poc.schemas import (
    PocDecisionCreate,
    PocDecisionResponse,
    PocMetricResponse,
    PocMetricUpdate,
    PocPlanResponse,
    PocPlanUpdate,
    PocReviewRequest,
    PocWorkspaceResponse,
)
from app.modules.solutions.router import serialize_proposal

router = APIRouter(tags=["poc"])


def serialize_metric(metric: PocMetric) -> PocMetricResponse:
    return PocMetricResponse(
        id=metric.id,
        metric_key=metric.metric_key,
        name=metric.name,
        target_operator=metric.target_operator,
        target_value=metric.target_value,
        unit=metric.unit,
        actual_value=metric.actual_value,
        result_status=metric.result_status,
        notes=metric.notes,
        position=metric.position,
        created_at=metric.created_at,
        updated_at=metric.updated_at,
    )


def serialize_decision(decision: PocDecision) -> PocDecisionResponse:
    return PocDecisionResponse(
        id=decision.id,
        decision=decision.decision,
        rationale=decision.rationale,
        created_at=decision.created_at,
    )


def serialize_plan(plan: PocPlan) -> PocPlanResponse:
    return PocPlanResponse(
        id=plan.id,
        account_id=plan.account_id,
        objective=plan.objective,
        business_problem=plan.business_problem,
        scope=plan.scope,
        required_data=plan.required_data,
        architecture=plan.architecture,
        timeline_days=plan.timeline_days,
        evaluation_dataset=plan.evaluation_dataset,
        expected_output=plan.expected_output,
        risks=plan.risks,
        status=plan.status,
        review_notes=plan.review_notes,
        reviewed_at=plan.reviewed_at,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        solution_proposal=serialize_proposal(plan.solution_proposal),
        metrics=[serialize_metric(metric) for metric in plan.metrics],
        decisions=[serialize_decision(decision) for decision in plan.decisions],
    )


def serialize_workspace(account_id: uuid.UUID, session: SessionDep) -> PocWorkspaceResponse:
    account, accepted_solution, plan, poc_state, evaluation_state = (
        service.get_poc_workspace(session, account_id)
    )
    return PocWorkspaceResponse(
        account_id=account_id,
        current_stage=account.current_stage,
        poc_stage_status=poc_state.status,
        evaluation_stage_status=evaluation_state.status,
        accepted_solution=(
            serialize_proposal(accepted_solution) if accepted_solution is not None else None
        ),
        plan=serialize_plan(plan) if plan is not None else None,
    )


def handle_error(exc: Exception) -> HTTPException:
    if isinstance(exc, accounts_service.AccountNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if isinstance(exc, service.PocNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(
        exc,
        (
            service.PocConflictError,
            service.PocPrerequisiteError,
            accounts_service.InvalidWorkflowTransitionError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, service.ArchivedAccountError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Archived account is read-only",
        )
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/accounts/{account_id}/poc", response_model=PocWorkspaceResponse)
def get_poc(account_id: uuid.UUID, session: SessionDep) -> PocWorkspaceResponse:
    try:
        return serialize_workspace(account_id, session)
    except Exception as exc:
        raise handle_error(exc) from exc


@router.post(
    "/accounts/{account_id}/poc-plans/generate",
    response_model=PocPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_poc_plan(account_id: uuid.UUID, session: SessionDep) -> PocPlanResponse:
    try:
        return serialize_plan(service.generate_plan(session, account_id))
    except Exception as exc:
        raise handle_error(exc) from exc


@router.patch("/poc-plans/{plan_id}", response_model=PocPlanResponse)
def patch_poc_plan(
    plan_id: uuid.UUID, payload: PocPlanUpdate, session: SessionDep
) -> PocPlanResponse:
    try:
        return serialize_plan(service.update_plan(session, plan_id, payload))
    except Exception as exc:
        raise handle_error(exc) from exc


@router.post("/poc-plans/{plan_id}/review", response_model=PocPlanResponse)
def post_poc_review(
    plan_id: uuid.UUID, payload: PocReviewRequest, session: SessionDep
) -> PocPlanResponse:
    try:
        return serialize_plan(service.review_plan(session, plan_id, payload))
    except Exception as exc:
        raise handle_error(exc) from exc


@router.patch("/poc-metrics/{metric_id}", response_model=PocPlanResponse)
def patch_poc_metric(
    metric_id: uuid.UUID, payload: PocMetricUpdate, session: SessionDep
) -> PocPlanResponse:
    try:
        return serialize_plan(service.update_metric(session, metric_id, payload))
    except Exception as exc:
        raise handle_error(exc) from exc


@router.post("/poc-plans/{plan_id}/decision", response_model=PocPlanResponse)
def post_poc_decision(
    plan_id: uuid.UUID, payload: PocDecisionCreate, session: SessionDep
) -> PocPlanResponse:
    try:
        return serialize_plan(service.create_decision(session, plan_id, payload))
    except Exception as exc:
        raise handle_error(exc) from exc
