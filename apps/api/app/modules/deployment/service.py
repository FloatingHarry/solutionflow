import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.accounts import service as accounts_service
from app.modules.accounts.enums import StageName, StageStatus
from app.modules.accounts.schemas import WorkflowTransitionRequest
from app.modules.business_case.enums import BusinessCaseStatus
from app.modules.business_case.models import BusinessCase
from app.modules.deployment.enums import ChecklistItemStatus, DeploymentPlanStatus
from app.modules.deployment.models import DeploymentChecklistItem, DeploymentPlan
from app.modules.deployment.schemas import (
    DeploymentChecklistUpdate,
    DeploymentCompleteRequest,
    DeploymentPlanUpdate,
)


class DeploymentNotFoundError(Exception):
    pass


class DeploymentConflictError(Exception):
    pass


class DeploymentPrerequisiteError(Exception):
    pass


class ArchivedAccountError(Exception):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC)


def _workflow_state(session: Session, account_id: uuid.UUID):
    _account, stages = accounts_service.get_workflow(session, account_id)
    return next(state for state in stages if state.stage == StageName.DEPLOYMENT)


def _ensure_editable(session: Session, account_id: uuid.UUID) -> None:
    account = accounts_service.get_account_or_raise(session, account_id)
    if account.archived_at is not None:
        raise ArchivedAccountError


def _plan_options():
    return (selectinload(DeploymentPlan.checklist_items),)


def get_plan_or_raise(session: Session, plan_id: uuid.UUID) -> DeploymentPlan:
    plan = session.scalar(
        select(DeploymentPlan)
        .where(DeploymentPlan.id == plan_id)
        .options(*_plan_options())
        .execution_options(populate_existing=True)
    )
    if plan is None:
        raise DeploymentNotFoundError("Deployment plan not found")
    return plan


def get_item_or_raise(session: Session, item_id: uuid.UUID) -> DeploymentChecklistItem:
    item = session.scalar(
        select(DeploymentChecklistItem)
        .where(DeploymentChecklistItem.id == item_id)
        .options(selectinload(DeploymentChecklistItem.deployment_plan))
    )
    if item is None:
        raise DeploymentNotFoundError("Deployment checklist item not found")
    return item


def _approved_business_case(session: Session, account_id: uuid.UUID) -> BusinessCase | None:
    return session.scalar(
        select(BusinessCase)
        .where(
            BusinessCase.account_id == account_id,
            BusinessCase.status == BusinessCaseStatus.APPROVED,
        )
        .order_by(BusinessCase.reviewed_at.desc())
    )


def get_workspace(session: Session, account_id: uuid.UUID):
    account = accounts_service.get_account_or_raise(session, account_id)
    case = _approved_business_case(session, account_id)
    plan = session.scalar(
        select(DeploymentPlan)
        .where(DeploymentPlan.account_id == account_id)
        .options(*_plan_options())
    )
    return account, _workflow_state(session, account_id), case, plan


CHECKLIST = [
    ("security", "Security architecture and least-privilege access approved"),
    ("privacy", "Data residency, retention, and deletion controls validated"),
    ("procurement", "Provider, commercial, and procurement terms approved"),
    ("integration", "Production integrations and data contracts validated"),
    ("operations", "Monitoring, alerting, and rollback procedure rehearsed"),
    ("governance", "Human review, escalation, and support owners trained"),
]


def _start_stage(session: Session, account_id: uuid.UUID) -> None:
    state = _workflow_state(session, account_id)
    if state.status in {StageStatus.NOT_STARTED, StageStatus.BLOCKED}:
        accounts_service.transition_workflow(
            session,
            account_id,
            WorkflowTransitionRequest(
                stage=StageName.DEPLOYMENT,
                status=StageStatus.IN_PROGRESS,
                reason="Deployment plan created from the approved business case",
            ),
        )


def generate_plan(session: Session, account_id: uuid.UUID) -> DeploymentPlan:
    _ensure_editable(session, account_id)
    case = _approved_business_case(session, account_id)
    if case is None:
        raise DeploymentPrerequisiteError(
            "Approve the business case before creating a deployment plan"
        )
    if session.scalar(select(DeploymentPlan.id).where(DeploymentPlan.account_id == account_id)):
        raise DeploymentConflictError("A deployment plan already exists for this account")

    _start_stage(session, account_id)
    environment = case.recommended_deployment.value.replace("_", " ")
    plan = DeploymentPlan(
        account_id=account_id,
        business_case_id=case.id,
        environment=case.recommended_deployment,
        owner="Deployment owner to confirm",
        rollout_strategy=(
            "Controlled rollout: internal validation, limited production cohort, monitored "
            "expansion, then general availability after the exit criteria pass."
        ),
        integration_plan=(
            "Validate authentication, production data contracts, downstream exports, retry "
            "behavior, and human exception routing before launch."
        ),
        data_governance_plan=(
            f"Apply the approved {environment} boundary, least-privilege access, documented "
            "retention, deletion, audit, and residency controls."
        ),
        monitoring_plan=(
            "Monitor availability, latency, cost, quality metrics, exception rate, and human "
            "override volume with named alert owners."
        ),
        rollback_plan=(
            "Keep the existing workflow available, define stop conditions, preserve reversible "
            "data changes, and rehearse traffic rollback before launch."
        ),
        support_model=(
            "Assign business, engineering, security, and support ownership with incident, model "
            "quality, and change-management escalation paths."
        ),
    )
    for position, (category, title) in enumerate(CHECKLIST):
        plan.checklist_items.append(
            DeploymentChecklistItem(category=category, title=title, position=position)
        )
    session.add(plan)
    session.flush()
    accounts_service.add_activity(
        session,
        account_id=account_id,
        event_type="deployment.plan_generated",
        entity_type="deployment_plan",
        entity_id=str(plan.id),
        summary="Deployment plan and production-readiness checklist generated",
        metadata={
            "business_case_id": str(case.id),
            "environment": case.recommended_deployment.value,
            "checklist_count": len(CHECKLIST),
        },
    )
    session.commit()
    return get_plan_or_raise(session, plan.id)


def _ensure_plan_editable(plan: DeploymentPlan) -> None:
    if plan.status == DeploymentPlanStatus.COMPLETED:
        raise DeploymentConflictError("A completed deployment plan is read-only")


def update_plan(
    session: Session, plan_id: uuid.UUID, payload: DeploymentPlanUpdate
) -> DeploymentPlan:
    plan = get_plan_or_raise(session, plan_id)
    _ensure_editable(session, plan.account_id)
    _ensure_plan_editable(plan)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(plan, field, value)
    plan.updated_at = utc_now()
    accounts_service.add_activity(
        session,
        account_id=plan.account_id,
        event_type="deployment.plan_updated",
        entity_type="deployment_plan",
        entity_id=str(plan.id),
        summary="Deployment operating plan updated",
    )
    session.commit()
    return get_plan_or_raise(session, plan.id)


def _recalculate_readiness(plan: DeploymentPlan) -> None:
    completed = sum(
        item.status == ChecklistItemStatus.COMPLETED for item in plan.checklist_items
    )
    plan.readiness_score = round(completed / len(plan.checklist_items) * 100)
    plan.status = (
        DeploymentPlanStatus.BLOCKED
        if any(item.status == ChecklistItemStatus.BLOCKED for item in plan.checklist_items)
        else DeploymentPlanStatus.IN_PROGRESS
    )
    plan.updated_at = utc_now()


def update_checklist_item(
    session: Session, item_id: uuid.UUID, payload: DeploymentChecklistUpdate
) -> DeploymentPlan:
    item = get_item_or_raise(session, item_id)
    plan = get_plan_or_raise(session, item.deployment_plan_id)
    _ensure_editable(session, plan.account_id)
    _ensure_plan_editable(plan)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    item.completed_at = utc_now() if item.status == ChecklistItemStatus.COMPLETED else None
    item.updated_at = utc_now()
    _recalculate_readiness(plan)
    accounts_service.add_activity(
        session,
        account_id=plan.account_id,
        event_type="deployment.checklist_updated",
        entity_type="deployment_checklist_item",
        entity_id=str(item.id),
        summary=f"Deployment check updated: {item.title}",
        metadata={"category": item.category, "status": item.status.value},
    )
    session.commit()

    stage = _workflow_state(session, plan.account_id)
    if plan.status == DeploymentPlanStatus.BLOCKED and stage.status == StageStatus.IN_PROGRESS:
        accounts_service.transition_workflow(
            session,
            plan.account_id,
            WorkflowTransitionRequest(
                stage=StageName.DEPLOYMENT,
                status=StageStatus.BLOCKED,
                reason=f"Deployment check blocked: {item.title}",
            ),
        )
    elif plan.status == DeploymentPlanStatus.IN_PROGRESS and stage.status == StageStatus.BLOCKED:
        accounts_service.transition_workflow(
            session,
            plan.account_id,
            WorkflowTransitionRequest(
                stage=StageName.DEPLOYMENT,
                status=StageStatus.IN_PROGRESS,
                reason="Deployment blockers cleared",
            ),
        )
    return get_plan_or_raise(session, plan.id)


def complete_plan(
    session: Session, plan_id: uuid.UUID, payload: DeploymentCompleteRequest
) -> DeploymentPlan:
    plan = get_plan_or_raise(session, plan_id)
    _ensure_editable(session, plan.account_id)
    _ensure_plan_editable(plan)
    incomplete = [
        item.title
        for item in plan.checklist_items
        if item.status != ChecklistItemStatus.COMPLETED
    ]
    if incomplete:
        raise DeploymentConflictError(
            "Complete every deployment readiness check first: " + ", ".join(incomplete)
        )
    now = utc_now()
    plan.status = DeploymentPlanStatus.COMPLETED
    plan.readiness_score = 100
    plan.completion_notes = payload.notes
    plan.completed_at = now
    plan.updated_at = now
    accounts_service.add_activity(
        session,
        account_id=plan.account_id,
        event_type="deployment.completed",
        entity_type="deployment_plan",
        entity_id=str(plan.id),
        summary="Deployment readiness plan completed",
        metadata={"notes": payload.notes, "readiness_score": 100},
    )
    session.commit()
    accounts_service.transition_workflow(
        session,
        plan.account_id,
        WorkflowTransitionRequest(
            stage=StageName.DEPLOYMENT,
            status=StageStatus.COMPLETED,
            reason=payload.notes,
        ),
    )
    return get_plan_or_raise(session, plan.id)
