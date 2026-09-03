import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.accounts import service as accounts_service
from app.modules.accounts.enums import StageName, StageStatus
from app.modules.accounts.schemas import WorkflowTransitionRequest
from app.modules.poc.enums import (
    MetricOperator,
    MetricResultStatus,
    PocDecisionType,
    PocPlanStatus,
    PocReviewDecision,
)
from app.modules.poc.models import PocDecision, PocMetric, PocPlan
from app.modules.poc.schemas import (
    PocDecisionCreate,
    PocMetricUpdate,
    PocPlanUpdate,
    PocReviewRequest,
)
from app.modules.solutions.enums import SolutionProposalStatus
from app.modules.solutions.models import SolutionProposal


class PocNotFoundError(Exception):
    pass


class PocConflictError(Exception):
    pass


class PocPrerequisiteError(Exception):
    pass


class ArchivedAccountError(Exception):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC)


def _workflow_state(session: Session, account_id: uuid.UUID, stage: StageName):
    _account, stages = accounts_service.get_workflow(session, account_id)
    return next(state for state in stages if state.stage == stage)


def _ensure_editable(session: Session, account_id: uuid.UUID) -> None:
    account = accounts_service.get_account_or_raise(session, account_id)
    if account.archived_at is not None:
        raise ArchivedAccountError


def get_accepted_solution(
    session: Session, account_id: uuid.UUID
) -> SolutionProposal | None:
    return session.scalar(
        select(SolutionProposal)
        .where(
            SolutionProposal.account_id == account_id,
            SolutionProposal.status == SolutionProposalStatus.ACCEPTED,
        )
        .options(
            selectinload(SolutionProposal.solution_template),
            selectinload(SolutionProposal.derived_needs),
        )
        .order_by(SolutionProposal.reviewed_at.desc())
    )


def get_plan_or_raise(session: Session, plan_id: uuid.UUID) -> PocPlan:
    plan = session.scalar(
        select(PocPlan)
        .where(PocPlan.id == plan_id)
        .options(
            selectinload(PocPlan.solution_proposal).selectinload(
                SolutionProposal.solution_template
            ),
            selectinload(PocPlan.solution_proposal).selectinload(
                SolutionProposal.derived_needs
            ),
            selectinload(PocPlan.metrics),
            selectinload(PocPlan.decisions),
        )
        .execution_options(populate_existing=True)
    )
    if plan is None:
        raise PocNotFoundError("POC plan not found")
    return plan


def get_metric_or_raise(session: Session, metric_id: uuid.UUID) -> PocMetric:
    metric = session.scalar(
        select(PocMetric)
        .where(PocMetric.id == metric_id)
        .options(selectinload(PocMetric.poc_plan))
    )
    if metric is None:
        raise PocNotFoundError("POC metric not found")
    return metric


def get_poc_workspace(session: Session, account_id: uuid.UUID):
    account = accounts_service.get_account_or_raise(session, account_id)
    accepted_solution = get_accepted_solution(session, account_id)
    plan = session.scalar(
        select(PocPlan)
        .where(PocPlan.account_id == account_id)
        .options(
            selectinload(PocPlan.solution_proposal).selectinload(
                SolutionProposal.solution_template
            ),
            selectinload(PocPlan.solution_proposal).selectinload(
                SolutionProposal.derived_needs
            ),
            selectinload(PocPlan.metrics),
            selectinload(PocPlan.decisions),
        )
        .order_by(PocPlan.created_at.desc())
    )
    poc_state = _workflow_state(session, account_id, StageName.POC)
    evaluation_state = _workflow_state(session, account_id, StageName.EVALUATION)
    return account, accepted_solution, plan, poc_state, evaluation_state


METRIC_TEMPLATES: dict[str, list[dict]] = {
    "document-intelligence": [
        {
            "metric_key": "field_extraction_accuracy",
            "name": "Field extraction accuracy",
            "target_operator": MetricOperator.GREATER_THAN_OR_EQUAL,
            "target_value": 90,
            "unit": "%",
        },
        {
            "metric_key": "straight_through_processing",
            "name": "Straight-through processing",
            "target_operator": MetricOperator.GREATER_THAN_OR_EQUAL,
            "target_value": 70,
            "unit": "%",
        },
        {
            "metric_key": "processing_lead_time",
            "name": "Processing lead time",
            "target_operator": MetricOperator.LESS_THAN_OR_EQUAL,
            "target_value": 1,
            "unit": "day",
        },
        {
            "metric_key": "human_rating",
            "name": "Human rating",
            "target_operator": MetricOperator.GREATER_THAN_OR_EQUAL,
            "target_value": 4,
            "unit": "/5",
        },
    ],
    "enterprise-knowledge-assistant": [
        {
            "metric_key": "task_success_rate",
            "name": "Task success rate",
            "target_operator": MetricOperator.GREATER_THAN_OR_EQUAL,
            "target_value": 80,
            "unit": "%",
        },
        {
            "metric_key": "citation_accuracy",
            "name": "Citation accuracy",
            "target_operator": MetricOperator.GREATER_THAN_OR_EQUAL,
            "target_value": 90,
            "unit": "%",
        },
        {
            "metric_key": "median_answer_time",
            "name": "Median answer time",
            "target_operator": MetricOperator.LESS_THAN_OR_EQUAL,
            "target_value": 30,
            "unit": "sec",
        },
        {
            "metric_key": "human_rating",
            "name": "Human rating",
            "target_operator": MetricOperator.GREATER_THAN_OR_EQUAL,
            "target_value": 4,
            "unit": "/5",
        },
    ],
    "customer-service-copilot": [
        {
            "metric_key": "handling_time_reduction",
            "name": "Handling time reduction",
            "target_operator": MetricOperator.GREATER_THAN_OR_EQUAL,
            "target_value": 25,
            "unit": "%",
        },
        {
            "metric_key": "agent_acceptance",
            "name": "Agent acceptance",
            "target_operator": MetricOperator.GREATER_THAN_OR_EQUAL,
            "target_value": 70,
            "unit": "%",
        },
        {
            "metric_key": "first_contact_resolution",
            "name": "First-contact resolution",
            "target_operator": MetricOperator.GREATER_THAN_OR_EQUAL,
            "target_value": 75,
            "unit": "%",
        },
        {
            "metric_key": "human_rating",
            "name": "Human rating",
            "target_operator": MetricOperator.GREATER_THAN_OR_EQUAL,
            "target_value": 4,
            "unit": "/5",
        },
    ],
    "sales-account-copilot": [
        {
            "metric_key": "research_time_reduction",
            "name": "Research time reduction",
            "target_operator": MetricOperator.GREATER_THAN_OR_EQUAL,
            "target_value": 50,
            "unit": "%",
        },
        {
            "metric_key": "evidence_coverage",
            "name": "Evidence coverage",
            "target_operator": MetricOperator.GREATER_THAN_OR_EQUAL,
            "target_value": 90,
            "unit": "%",
        },
        {
            "metric_key": "seller_rating",
            "name": "Seller rating",
            "target_operator": MetricOperator.GREATER_THAN_OR_EQUAL,
            "target_value": 4,
            "unit": "/5",
        },
        {
            "metric_key": "task_success_rate",
            "name": "Task success rate",
            "target_operator": MetricOperator.GREATER_THAN_OR_EQUAL,
            "target_value": 80,
            "unit": "%",
        },
    ],
}


def _start_stage(
    session: Session, account_id: uuid.UUID, stage: StageName, reason: str
) -> None:
    state = _workflow_state(session, account_id, stage)
    if state.status in {StageStatus.NOT_STARTED, StageStatus.BLOCKED}:
        accounts_service.transition_workflow(
            session,
            account_id,
            WorkflowTransitionRequest(
                stage=stage,
                status=StageStatus.IN_PROGRESS,
                reason=reason,
            ),
        )


def generate_plan(session: Session, account_id: uuid.UUID) -> PocPlan:
    _ensure_editable(session, account_id)
    accepted = get_accepted_solution(session, account_id)
    if accepted is None:
        raise PocPrerequisiteError("Accept a solution proposal before generating a POC plan")
    existing_id = session.scalar(
        select(PocPlan.id).where(PocPlan.solution_proposal_id == accepted.id)
    )
    if existing_id is not None:
        raise PocConflictError("A POC plan already exists for the accepted solution")

    _start_stage(
        session,
        account_id,
        StageName.POC,
        "POC planning started from the accepted solution proposal",
    )
    need_titles = ", ".join(need.title for need in accepted.derived_needs)
    need_descriptions = "; ".join(need.description for need in accepted.derived_needs)
    plan = PocPlan(
        account_id=account_id,
        solution_proposal_id=accepted.id,
        objective=(
            f"Validate whether {accepted.title} can meet the agreed success criteria "
            "with representative data before production investment."
        ),
        business_problem=need_descriptions or accepted.executive_summary,
        scope=(
            f"Build and test a constrained prototype for: {need_titles}. "
            "Exclude production integrations, autonomous actions, and full-scale rollout."
        ),
        required_data=list(accepted.required_data),
        architecture=accepted.architecture,
        timeline_days=14,
        evaluation_dataset=(
            "A representative, access-approved holdout set covering normal cases, edge cases, "
            "and known exceptions; it must remain separate from development examples."
        ),
        expected_output=(
            "A working prototype, reproducible metric results, documented exceptions, "
            "and a human Proceed / Iterate / Reject decision."
        ),
        risks=list(accepted.risks),
        status=PocPlanStatus.DRAFT,
    )
    for position, metric in enumerate(METRIC_TEMPLATES[accepted.solution_template.slug]):
        plan.metrics.append(PocMetric(**metric, position=position))
    session.add(plan)
    session.flush()
    accounts_service.add_activity(
        session,
        account_id=account_id,
        event_type="poc.plan_generated",
        entity_type="poc_plan",
        entity_id=str(plan.id),
        summary=f"Draft POC plan generated from accepted solution: {accepted.title}",
        metadata={
            "solution_proposal_id": str(accepted.id),
            "derived_from_need_ids": [str(need.id) for need in accepted.derived_needs],
            "metric_count": len(plan.metrics),
        },
    )
    session.commit()
    return get_plan_or_raise(session, plan.id)


def update_plan(session: Session, plan_id: uuid.UUID, payload: PocPlanUpdate) -> PocPlan:
    plan = get_plan_or_raise(session, plan_id)
    _ensure_editable(session, plan.account_id)
    if plan.status not in {PocPlanStatus.DRAFT, PocPlanStatus.NEEDS_REVISION}:
        raise PocConflictError("Only draft or revision POC plans can be edited")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(plan, field, value)
    plan.updated_at = utc_now()
    accounts_service.add_activity(
        session,
        account_id=plan.account_id,
        event_type="poc.plan_updated",
        entity_type="poc_plan",
        entity_id=str(plan.id),
        summary="POC plan updated",
    )
    session.commit()
    return get_plan_or_raise(session, plan.id)


def review_plan(session: Session, plan_id: uuid.UUID, payload: PocReviewRequest) -> PocPlan:
    plan = get_plan_or_raise(session, plan_id)
    _ensure_editable(session, plan.account_id)
    if plan.status not in {PocPlanStatus.DRAFT, PocPlanStatus.NEEDS_REVISION}:
        raise PocConflictError("This POC plan is not awaiting review")

    plan.status = {
        PocReviewDecision.APPROVE: PocPlanStatus.APPROVED,
        PocReviewDecision.NEEDS_REVISION: PocPlanStatus.NEEDS_REVISION,
        PocReviewDecision.REJECT: PocPlanStatus.REJECTED,
    }[payload.decision]
    plan.review_notes = payload.notes
    plan.reviewed_at = utc_now()
    plan.updated_at = plan.reviewed_at
    accounts_service.add_activity(
        session,
        account_id=plan.account_id,
        event_type=f"poc.plan_{plan.status.value}",
        entity_type="poc_plan",
        entity_id=str(plan.id),
        summary=f"POC plan marked {plan.status.value.replace('_', ' ')}",
        metadata={"notes": payload.notes},
    )
    session.commit()

    poc_state = _workflow_state(session, plan.account_id, StageName.POC)
    if payload.decision == PocReviewDecision.APPROVE:
        accounts_service.transition_workflow(
            session,
            plan.account_id,
            WorkflowTransitionRequest(
                stage=StageName.POC,
                status=StageStatus.COMPLETED,
                reason=payload.notes,
            ),
        )
        _start_stage(
            session,
            plan.account_id,
            StageName.EVALUATION,
            "POC plan approved; evaluation started",
        )
    elif poc_state.status == StageStatus.IN_PROGRESS:
        accounts_service.transition_workflow(
            session,
            plan.account_id,
            WorkflowTransitionRequest(
                stage=StageName.POC,
                status=StageStatus.BLOCKED,
                reason=payload.notes,
            ),
        )
    return get_plan_or_raise(session, plan.id)


def update_metric(
    session: Session, metric_id: uuid.UUID, payload: PocMetricUpdate
) -> PocPlan:
    metric = get_metric_or_raise(session, metric_id)
    plan = metric.poc_plan
    _ensure_editable(session, plan.account_id)
    evaluation_state = _workflow_state(session, plan.account_id, StageName.EVALUATION)
    if evaluation_state.status == StageStatus.COMPLETED:
        raise PocConflictError("A completed evaluation is read-only")

    fields = payload.model_fields_set
    target_fields = {"target_operator", "target_value", "unit"}
    if fields & target_fields and plan.status == PocPlanStatus.APPROVED:
        raise PocConflictError("Metric targets are locked after POC approval")
    if "actual_value" in fields:
        if plan.status != PocPlanStatus.APPROVED:
            raise PocPrerequisiteError("Approve the POC plan before recording results")
        if evaluation_state.status not in {StageStatus.IN_PROGRESS, StageStatus.BLOCKED}:
            raise PocPrerequisiteError("Start evaluation before recording results")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(metric, field, value)
    if "actual_value" in fields:
        if metric.actual_value is None:
            metric.result_status = MetricResultStatus.PENDING
        elif metric.target_operator == MetricOperator.GREATER_THAN_OR_EQUAL:
            metric.result_status = (
                MetricResultStatus.PASS
                if metric.actual_value >= metric.target_value
                else MetricResultStatus.FAIL
            )
        else:
            metric.result_status = (
                MetricResultStatus.PASS
                if metric.actual_value <= metric.target_value
                else MetricResultStatus.FAIL
            )
    metric.updated_at = utc_now()
    accounts_service.add_activity(
        session,
        account_id=plan.account_id,
        event_type="poc.metric_updated",
        entity_type="poc_metric",
        entity_id=str(metric.id),
        summary=f"Evaluation metric updated: {metric.name}",
        metadata={
            "actual_value": metric.actual_value,
            "result_status": metric.result_status.value,
        },
    )
    session.commit()
    if "actual_value" in fields and evaluation_state.status == StageStatus.BLOCKED:
        _start_stage(
            session,
            plan.account_id,
            StageName.EVALUATION,
            "Evaluation resumed after an updated metric result",
        )
    return get_plan_or_raise(session, plan.id)


def create_decision(
    session: Session, plan_id: uuid.UUID, payload: PocDecisionCreate
) -> PocPlan:
    plan = get_plan_or_raise(session, plan_id)
    _ensure_editable(session, plan.account_id)
    if plan.status != PocPlanStatus.APPROVED:
        raise PocPrerequisiteError("Approve the POC plan before making an evaluation decision")
    evaluation_state = _workflow_state(session, plan.account_id, StageName.EVALUATION)
    if evaluation_state.status == StageStatus.COMPLETED:
        raise PocConflictError("A completed evaluation is read-only")
    if evaluation_state.status not in {StageStatus.IN_PROGRESS, StageStatus.BLOCKED}:
        raise PocPrerequisiteError("Start evaluation before making a decision")
    pending = [metric.name for metric in plan.metrics if metric.actual_value is None]
    if pending:
        raise PocPrerequisiteError(
            "Record actual values for every metric before deciding: " + ", ".join(pending)
        )

    decision = PocDecision(
        account_id=plan.account_id,
        poc_plan_id=plan.id,
        decision=payload.decision,
        rationale=payload.rationale,
    )
    session.add(decision)
    session.flush()
    accounts_service.add_activity(
        session,
        account_id=plan.account_id,
        event_type=f"poc.decision_{payload.decision.value}",
        entity_type="poc_decision",
        entity_id=str(decision.id),
        summary=f"POC evaluation decision: {payload.decision.value.title()}",
        metadata={
            "rationale": payload.rationale,
            "metric_results": {
                metric.metric_key: metric.result_status.value for metric in plan.metrics
            },
        },
    )
    session.commit()

    target_status = (
        StageStatus.COMPLETED
        if payload.decision == PocDecisionType.PROCEED
        else StageStatus.BLOCKED
    )
    if evaluation_state.status != target_status:
        accounts_service.transition_workflow(
            session,
            plan.account_id,
            WorkflowTransitionRequest(
                stage=StageName.EVALUATION,
                status=target_status,
                reason=payload.rationale,
            ),
        )
    return get_plan_or_raise(session, plan.id)
