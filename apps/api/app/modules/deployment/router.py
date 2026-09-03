import uuid

from fastapi import APIRouter, HTTPException, status

from app.db.session import SessionDep
from app.modules.accounts import service as accounts_service
from app.modules.business_case.enums import BusinessCaseStatus
from app.modules.deployment import service
from app.modules.deployment.models import DeploymentChecklistItem, DeploymentPlan
from app.modules.deployment.schemas import (
    DeploymentChecklistResponse,
    DeploymentChecklistUpdate,
    DeploymentCompleteRequest,
    DeploymentPlanResponse,
    DeploymentPlanUpdate,
    DeploymentWorkspaceResponse,
)

router = APIRouter(tags=["deployment"])


def serialize_item(item: DeploymentChecklistItem) -> DeploymentChecklistResponse:
    return DeploymentChecklistResponse(
        id=item.id,
        category=item.category,
        title=item.title,
        owner=item.owner,
        status=item.status,
        evidence_notes=item.evidence_notes,
        position=item.position,
        completed_at=item.completed_at,
        updated_at=item.updated_at,
    )


def serialize_plan(plan: DeploymentPlan) -> DeploymentPlanResponse:
    return DeploymentPlanResponse(
        id=plan.id,
        account_id=plan.account_id,
        business_case_id=plan.business_case_id,
        environment=plan.environment,
        owner=plan.owner,
        target_launch_date=plan.target_launch_date,
        rollout_strategy=plan.rollout_strategy,
        integration_plan=plan.integration_plan,
        data_governance_plan=plan.data_governance_plan,
        monitoring_plan=plan.monitoring_plan,
        rollback_plan=plan.rollback_plan,
        support_model=plan.support_model,
        status=plan.status,
        readiness_score=plan.readiness_score,
        completion_notes=plan.completion_notes,
        completed_at=plan.completed_at,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        checklist_items=[serialize_item(item) for item in plan.checklist_items],
    )


def handle_error(exc: Exception) -> HTTPException:
    if isinstance(exc, accounts_service.AccountNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if isinstance(exc, service.DeploymentNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(
        exc,
        (
            service.DeploymentConflictError,
            service.DeploymentPrerequisiteError,
            accounts_service.InvalidWorkflowTransitionError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, service.ArchivedAccountError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Archived account is read-only"
        )
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/accounts/{account_id}/deployment", response_model=DeploymentWorkspaceResponse
)
def get_deployment(account_id: uuid.UUID, session: SessionDep) -> DeploymentWorkspaceResponse:
    try:
        account, stage, case, plan = service.get_workspace(session, account_id)
        return DeploymentWorkspaceResponse(
            account_id=account.id,
            current_stage=account.current_stage,
            deployment_stage_status=stage.status,
            business_case_approved=bool(case and case.status == BusinessCaseStatus.APPROVED),
            recommended_environment=case.recommended_deployment if case else None,
            plan=serialize_plan(plan) if plan else None,
        )
    except Exception as exc:
        raise handle_error(exc) from exc


@router.post(
    "/accounts/{account_id}/deployment-plans/generate",
    response_model=DeploymentPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_deployment_plan(
    account_id: uuid.UUID, session: SessionDep
) -> DeploymentPlanResponse:
    try:
        return serialize_plan(service.generate_plan(session, account_id))
    except Exception as exc:
        raise handle_error(exc) from exc


@router.patch("/deployment-plans/{plan_id}", response_model=DeploymentPlanResponse)
def patch_deployment_plan(
    plan_id: uuid.UUID, payload: DeploymentPlanUpdate, session: SessionDep
) -> DeploymentPlanResponse:
    try:
        return serialize_plan(service.update_plan(session, plan_id, payload))
    except Exception as exc:
        raise handle_error(exc) from exc


@router.patch(
    "/deployment-checklist-items/{item_id}", response_model=DeploymentPlanResponse
)
def patch_deployment_checklist(
    item_id: uuid.UUID, payload: DeploymentChecklistUpdate, session: SessionDep
) -> DeploymentPlanResponse:
    try:
        return serialize_plan(service.update_checklist_item(session, item_id, payload))
    except Exception as exc:
        raise handle_error(exc) from exc


@router.post(
    "/deployment-plans/{plan_id}/complete", response_model=DeploymentPlanResponse
)
def post_deployment_complete(
    plan_id: uuid.UUID, payload: DeploymentCompleteRequest, session: SessionDep
) -> DeploymentPlanResponse:
    try:
        return serialize_plan(service.complete_plan(session, plan_id, payload))
    except Exception as exc:
        raise handle_error(exc) from exc
