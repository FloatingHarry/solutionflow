import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.accounts import service as accounts_service
from app.modules.accounts.enums import StageName, StageStatus
from app.modules.accounts.schemas import WorkflowTransitionRequest
from app.modules.business_case.enums import (
    AssessmentRating,
    BusinessCaseReviewDecision,
    BusinessCaseStatus,
)
from app.modules.business_case.models import AccountBrief, BusinessCase, DeploymentAssessment
from app.modules.business_case.schemas import (
    AccountBriefUpdate,
    BusinessCaseReviewRequest,
    DeploymentRecommendationUpdate,
    RoiScenarioUpdate,
)
from app.modules.poc.enums import PocDecisionType, PocPlanStatus
from app.modules.poc.models import PocDecision, PocPlan
from app.modules.solutions.enums import DeploymentOption
from app.modules.solutions.models import SolutionProposal


class BusinessCaseNotFoundError(Exception):
    pass


class BusinessCaseConflictError(Exception):
    pass


class BusinessCasePrerequisiteError(Exception):
    pass


class ArchivedAccountError(Exception):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC)


def _workflow_state(session: Session, account_id: uuid.UUID, stage: StageName):
    _account, stages = accounts_service.get_workflow(session, account_id)
    return next(state for state in stages if state.stage == stage)


def _ensure_editable_account(session: Session, account_id: uuid.UUID) -> None:
    account = accounts_service.get_account_or_raise(session, account_id)
    if account.archived_at is not None:
        raise ArchivedAccountError


def _case_options():
    return (
        selectinload(BusinessCase.poc_plan)
        .selectinload(PocPlan.solution_proposal)
        .selectinload(SolutionProposal.solution_template),
        selectinload(BusinessCase.poc_plan)
        .selectinload(PocPlan.solution_proposal)
        .selectinload(SolutionProposal.derived_needs),
        selectinload(BusinessCase.poc_plan).selectinload(PocPlan.metrics),
        selectinload(BusinessCase.poc_plan).selectinload(PocPlan.decisions),
        selectinload(BusinessCase.deployment_assessments),
        selectinload(BusinessCase.brief),
    )


def get_case_or_raise(session: Session, case_id: uuid.UUID) -> BusinessCase:
    case = session.scalar(
        select(BusinessCase)
        .where(BusinessCase.id == case_id)
        .options(*_case_options())
        .execution_options(populate_existing=True)
    )
    if case is None:
        raise BusinessCaseNotFoundError("Business case not found")
    return case


def get_brief_or_raise(session: Session, brief_id: uuid.UUID) -> AccountBrief:
    brief = session.scalar(
        select(AccountBrief)
        .where(AccountBrief.id == brief_id)
        .options(selectinload(AccountBrief.business_case))
    )
    if brief is None:
        raise BusinessCaseNotFoundError("Account brief not found")
    return brief


def _completed_poc(session: Session, account_id: uuid.UUID) -> PocPlan | None:
    if _workflow_state(session, account_id, StageName.EVALUATION).status != StageStatus.COMPLETED:
        return None
    plan = session.scalar(
        select(PocPlan)
        .where(PocPlan.account_id == account_id, PocPlan.status == PocPlanStatus.APPROVED)
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
    if plan is None:
        return None
    latest_decision = session.scalar(
        select(PocDecision)
        .where(PocDecision.poc_plan_id == plan.id)
        .order_by(PocDecision.created_at.desc())
    )
    if latest_decision is None or latest_decision.decision != PocDecisionType.PROCEED:
        return None
    return plan


def get_workspace(session: Session, account_id: uuid.UUID):
    account = accounts_service.get_account_or_raise(session, account_id)
    case = session.scalar(
        select(BusinessCase)
        .where(BusinessCase.account_id == account_id)
        .options(*_case_options())
        .order_by(BusinessCase.created_at.desc())
    )
    business_state = _workflow_state(session, account_id, StageName.BUSINESS_CASE)
    deployment_state = _workflow_state(session, account_id, StageName.DEPLOYMENT)
    evaluation_completed = (
        _workflow_state(session, account_id, StageName.EVALUATION).status
        == StageStatus.COMPLETED
    )
    return account, case, business_state, deployment_state, evaluation_completed


def _round(value: float) -> float:
    return round(value, 2)


def calculate_roi(case: BusinessCase) -> None:
    current = (
        case.number_employees
        * case.tasks_per_employee_per_month
        * (case.current_time_per_task_minutes / 60)
        * case.average_hourly_cost
    )
    new_labor = current * (1 - case.expected_time_reduction_percent / 100)
    new_total = new_labor + case.monthly_ai_cost
    monthly_savings = current - new_total
    annual_savings = monthly_savings * 12
    case.current_monthly_cost = _round(current)
    case.estimated_new_labor_cost = _round(new_labor)
    case.estimated_new_total_cost = _round(new_total)
    case.monthly_savings = _round(monthly_savings)
    case.annual_savings = _round(annual_savings)
    case.estimated_first_year_roi_percent = (
        _round(((annual_savings - case.implementation_cost) / case.implementation_cost) * 100)
        if case.implementation_cost > 0
        else None
    )
    case.payback_period_months = (
        _round(case.implementation_cost / monthly_savings) if monthly_savings > 0 else None
    )


DEPLOYMENT_ASSESSMENTS = [
    {
        "option": DeploymentOption.SAAS_API,
        "cost": AssessmentRating.LOW,
        "implementation_difficulty": AssessmentRating.LOW,
        "data_privacy": AssessmentRating.MEDIUM,
        "scalability": AssessmentRating.HIGH,
        "maintenance": AssessmentRating.LOW,
        "latency": AssessmentRating.MEDIUM,
        "compliance": AssessmentRating.MEDIUM,
        "notes": [
            "Fastest path to a managed pilot and elastic scaling.",
            "Requires provider, residency, retention, and access-control review.",
        ],
    },
    {
        "option": DeploymentOption.EU_CLOUD,
        "cost": AssessmentRating.MEDIUM,
        "implementation_difficulty": AssessmentRating.MEDIUM,
        "data_privacy": AssessmentRating.HIGH,
        "scalability": AssessmentRating.HIGH,
        "maintenance": AssessmentRating.MEDIUM,
        "latency": AssessmentRating.MEDIUM,
        "compliance": AssessmentRating.HIGH,
        "notes": [
            "Balances managed operations with EU data-residency controls.",
            "Still requires documented subprocessors, retention, and audit boundaries.",
        ],
    },
    {
        "option": DeploymentOption.PRIVATE_ON_PREMISE,
        "cost": AssessmentRating.HIGH,
        "implementation_difficulty": AssessmentRating.HIGH,
        "data_privacy": AssessmentRating.HIGH,
        "scalability": AssessmentRating.MEDIUM,
        "maintenance": AssessmentRating.HIGH,
        "latency": AssessmentRating.LOW,
        "compliance": AssessmentRating.HIGH,
        "notes": [
            "Offers the strongest infrastructure control and local data boundary.",
            "Requires the highest platform, model-operations, security, and capacity effort.",
        ],
    },
]


def _currency_for_region(region: str | None) -> str:
    value = (region or "").lower()
    if "china" in value or "中国" in value:
        return "CNY"
    if "united kingdom" in value or value in {"uk", "gb"}:
        return "GBP"
    if "europe" in value or "eu" in value:
        return "EUR"
    return "USD"


def _default_costs(option: DeploymentOption) -> tuple[float, float]:
    return {
        DeploymentOption.SAAS_API: (1500, 25000),
        DeploymentOption.EU_CLOUD: (2800, 45000),
        DeploymentOption.PRIVATE_ON_PREMISE: (6500, 120000),
    }[option]


def _money(value: float, currency: str) -> str:
    return f"{currency} {value:,.0f}"


def _roi_summary(case: BusinessCase) -> str:
    roi = (
        f"{case.estimated_first_year_roi_percent:.1f}%"
        if case.estimated_first_year_roi_percent is not None
        else "not defined because implementation cost is zero"
    )
    payback = (
        f"{case.payback_period_months:.1f} months"
        if case.payback_period_months is not None
        else "not reached under the current assumptions"
    )
    return (
        "Scenario estimate only: current monthly labor cost is "
        f"{_money(case.current_monthly_cost, case.currency)}, estimated new total monthly "
        f"cost is {_money(case.estimated_new_total_cost, case.currency)}, annual savings are "
        f"{_money(case.annual_savings, case.currency)}, first-year ROI is {roi}, and estimated "
        f"payback is {payback}. These values are assumptions, not realized customer results."
    )


def _deployment_summary(case: BusinessCase) -> str:
    label = case.recommended_deployment.value.replace("_", " ").title()
    return f"Recommended deployment: {label}. {case.deployment_rationale}"


def _start_business_case(session: Session, account_id: uuid.UUID) -> None:
    state = _workflow_state(session, account_id, StageName.BUSINESS_CASE)
    if state.status in {StageStatus.NOT_STARTED, StageStatus.BLOCKED}:
        accounts_service.transition_workflow(
            session,
            account_id,
            WorkflowTransitionRequest(
                stage=StageName.BUSINESS_CASE,
                status=StageStatus.IN_PROGRESS,
                reason="Business case generated from a completed POC evaluation",
            ),
        )


def generate_case(session: Session, account_id: uuid.UUID) -> BusinessCase:
    _ensure_editable_account(session, account_id)
    plan = _completed_poc(session, account_id)
    if plan is None:
        raise BusinessCasePrerequisiteError(
            "Complete POC evaluation with a Proceed decision before generating a business case"
        )
    existing_id = session.scalar(
        select(BusinessCase.id).where(BusinessCase.poc_plan_id == plan.id)
    )
    if existing_id is not None:
        raise BusinessCaseConflictError("A business case already exists for this POC")

    _start_business_case(session, account_id)
    account = accounts_service.get_account_or_raise(session, account_id)
    proposal = plan.solution_proposal
    monthly_ai_cost, implementation_cost = _default_costs(proposal.deployment_option)
    deployment_label = proposal.deployment_option.value.replace("_", " ")
    case = BusinessCase(
        account_id=account_id,
        poc_plan_id=plan.id,
        currency=_currency_for_region(account.region),
        number_employees=25,
        average_hourly_cost=45,
        current_time_per_task_minutes=45,
        tasks_per_employee_per_month=20,
        expected_time_reduction_percent=50,
        monthly_ai_cost=monthly_ai_cost,
        implementation_cost=implementation_cost,
        current_monthly_cost=0,
        estimated_new_labor_cost=0,
        estimated_new_total_cost=0,
        monthly_savings=0,
        annual_savings=0,
        recommended_deployment=proposal.deployment_option,
        deployment_rationale=(
            f"Retain the accepted {deployment_label} option because it matches the approved "
            "solution boundary and POC. Validate procurement, security, residency, and "
            "operating ownership before production deployment."
        ),
        assumptions=[
            "All ROI values are editable scenario assumptions, not realized customer outcomes.",
            "Tasks per month is interpreted per participating employee.",
            "Time reduction is applied only to modeled task labor, not total role capacity.",
            "Monthly AI cost excludes taxes and unplanned integration change requests.",
        ],
        status=BusinessCaseStatus.DRAFT,
    )
    calculate_roi(case)
    for position, assessment in enumerate(DEPLOYMENT_ASSESSMENTS):
        case.deployment_assessments.append(
            DeploymentAssessment(**assessment, position=position)
        )
    metric_summary = "; ".join(
        f"{metric.name}: {metric.actual_value:g} {metric.unit} ({metric.result_status.value})"
        for metric in plan.metrics
        if metric.actual_value is not None
    )
    need_summary = "; ".join(
        f"{need.title} — success metric: {need.success_metric}"
        for need in proposal.derived_needs
    )
    case.brief = AccountBrief(
        account_id=account_id,
        executive_summary=(
            f"{account.name} has an accepted {proposal.solution_template.name} solution and a "
            "completed POC with a human Proceed decision. The next gate is to validate the "
            "scenario economics and deployment ownership before production work."
        ),
        customer_context=(
            f"Account-entered context: {account.name}; industry: {account.industry or 'not set'}; "
            f"region: {account.region or 'not set'}. {account.notes or 'No internal notes.'}"
        ),
        confirmed_needs_summary=need_summary,
        solution_summary=(
            f"Accepted solution: {proposal.title}. Architecture: {proposal.architecture}. "
            f"Expected impact: {proposal.expected_business_impact}"
        ),
        poc_summary=(
            f"Approved {plan.timeline_days}-day POC. Evaluation results: {metric_summary}. "
            "Final human decision: Proceed."
        ),
        roi_summary=_roi_summary(case),
        deployment_summary=_deployment_summary(case),
        key_risks=list(dict.fromkeys([*proposal.risks, *plan.risks])),
        next_steps=[
            "Validate every ROI assumption with finance and process owners.",
            "Complete security, privacy, procurement, and data-residency review.",
            "Confirm production data ownership, integration scope, and operating support model.",
            "Approve the final account brief before starting Deployment.",
        ],
    )
    session.add(case)
    session.flush()
    accounts_service.add_activity(
        session,
        account_id=account_id,
        event_type="business_case.generated",
        entity_type="business_case",
        entity_id=str(case.id),
        summary="Scenario ROI, deployment comparison, and final account brief generated",
        metadata={
            "poc_plan_id": str(plan.id),
            "solution_proposal_id": str(proposal.id),
            "derived_from_need_ids": [str(need.id) for need in proposal.derived_needs],
            "scenario_is_estimate": True,
        },
    )
    session.commit()
    return get_case_or_raise(session, case.id)


def _ensure_case_editable(case: BusinessCase) -> None:
    if case.status not in {BusinessCaseStatus.DRAFT, BusinessCaseStatus.NEEDS_REVISION}:
        raise BusinessCaseConflictError("Only draft or revision business cases can be edited")


def update_scenario(
    session: Session, case_id: uuid.UUID, payload: RoiScenarioUpdate
) -> BusinessCase:
    case = get_case_or_raise(session, case_id)
    _ensure_editable_account(session, case.account_id)
    _ensure_case_editable(case)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(case, field, value)
    calculate_roi(case)
    case.brief.roi_summary = _roi_summary(case)
    case.brief.updated_at = utc_now()
    case.updated_at = utc_now()
    accounts_service.add_activity(
        session,
        account_id=case.account_id,
        event_type="business_case.scenario_updated",
        entity_type="business_case",
        entity_id=str(case.id),
        summary="ROI scenario assumptions recalculated",
        metadata={"scenario_is_estimate": True},
    )
    session.commit()
    return get_case_or_raise(session, case.id)


def update_deployment(
    session: Session,
    case_id: uuid.UUID,
    payload: DeploymentRecommendationUpdate,
) -> BusinessCase:
    case = get_case_or_raise(session, case_id)
    _ensure_editable_account(session, case.account_id)
    _ensure_case_editable(case)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(case, field, value)
    case.brief.deployment_summary = _deployment_summary(case)
    case.brief.updated_at = utc_now()
    case.updated_at = utc_now()
    accounts_service.add_activity(
        session,
        account_id=case.account_id,
        event_type="business_case.deployment_updated",
        entity_type="business_case",
        entity_id=str(case.id),
        summary="Deployment recommendation updated",
        metadata={"recommended_deployment": case.recommended_deployment.value},
    )
    session.commit()
    return get_case_or_raise(session, case.id)


def update_brief(
    session: Session, brief_id: uuid.UUID, payload: AccountBriefUpdate
) -> BusinessCase:
    brief = get_brief_or_raise(session, brief_id)
    case = brief.business_case
    _ensure_editable_account(session, case.account_id)
    _ensure_case_editable(case)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(brief, field, value)
    brief.updated_at = utc_now()
    case.updated_at = brief.updated_at
    accounts_service.add_activity(
        session,
        account_id=case.account_id,
        event_type="business_case.brief_updated",
        entity_type="account_brief",
        entity_id=str(brief.id),
        summary="Final account brief updated",
    )
    session.commit()
    return get_case_or_raise(session, case.id)


def review_case(
    session: Session, case_id: uuid.UUID, payload: BusinessCaseReviewRequest
) -> BusinessCase:
    case = get_case_or_raise(session, case_id)
    _ensure_editable_account(session, case.account_id)
    _ensure_case_editable(case)
    case.status = {
        BusinessCaseReviewDecision.APPROVE: BusinessCaseStatus.APPROVED,
        BusinessCaseReviewDecision.NEEDS_REVISION: BusinessCaseStatus.NEEDS_REVISION,
        BusinessCaseReviewDecision.REJECT: BusinessCaseStatus.REJECTED,
    }[payload.decision]
    case.review_notes = payload.notes
    case.reviewed_at = utc_now()
    case.updated_at = case.reviewed_at
    accounts_service.add_activity(
        session,
        account_id=case.account_id,
        event_type=f"business_case.{case.status.value}",
        entity_type="business_case",
        entity_id=str(case.id),
        summary=f"Business case marked {case.status.value.replace('_', ' ')}",
        metadata={"notes": payload.notes, "scenario_is_estimate": True},
    )
    session.commit()

    state = _workflow_state(session, case.account_id, StageName.BUSINESS_CASE)
    if payload.decision == BusinessCaseReviewDecision.APPROVE:
        accounts_service.transition_workflow(
            session,
            case.account_id,
            WorkflowTransitionRequest(
                stage=StageName.BUSINESS_CASE,
                status=StageStatus.COMPLETED,
                reason=payload.notes,
            ),
        )
    elif state.status == StageStatus.IN_PROGRESS:
        accounts_service.transition_workflow(
            session,
            case.account_id,
            WorkflowTransitionRequest(
                stage=StageName.BUSINESS_CASE,
                status=StageStatus.BLOCKED,
                reason=payload.notes,
            ),
        )
    return get_case_or_raise(session, case.id)
