import uuid

from fastapi import APIRouter, HTTPException, status

from app.db.session import SessionDep
from app.modules.accounts import service as accounts_service
from app.modules.business_case import service
from app.modules.business_case.models import AccountBrief, BusinessCase, DeploymentAssessment
from app.modules.business_case.schemas import (
    AccountBriefResponse,
    AccountBriefUpdate,
    BusinessCaseResponse,
    BusinessCaseReviewRequest,
    BusinessCaseWorkspaceResponse,
    DeploymentAssessmentResponse,
    DeploymentRecommendationUpdate,
    RoiScenarioUpdate,
)
from app.modules.poc.router import serialize_plan

router = APIRouter(tags=["business-case"])


def serialize_assessment(assessment: DeploymentAssessment) -> DeploymentAssessmentResponse:
    return DeploymentAssessmentResponse(
        id=assessment.id,
        option=assessment.option,
        cost=assessment.cost,
        implementation_difficulty=assessment.implementation_difficulty,
        data_privacy=assessment.data_privacy,
        scalability=assessment.scalability,
        maintenance=assessment.maintenance,
        latency=assessment.latency,
        compliance=assessment.compliance,
        notes=assessment.notes,
        position=assessment.position,
    )


def serialize_brief(brief: AccountBrief) -> AccountBriefResponse:
    return AccountBriefResponse(
        id=brief.id,
        executive_summary=brief.executive_summary,
        customer_context=brief.customer_context,
        confirmed_needs_summary=brief.confirmed_needs_summary,
        solution_summary=brief.solution_summary,
        poc_summary=brief.poc_summary,
        roi_summary=brief.roi_summary,
        deployment_summary=brief.deployment_summary,
        key_risks=brief.key_risks,
        next_steps=brief.next_steps,
        created_at=brief.created_at,
        updated_at=brief.updated_at,
    )


def serialize_case(case: BusinessCase) -> BusinessCaseResponse:
    return BusinessCaseResponse(
        id=case.id,
        account_id=case.account_id,
        currency=case.currency,
        number_employees=case.number_employees,
        average_hourly_cost=case.average_hourly_cost,
        current_time_per_task_minutes=case.current_time_per_task_minutes,
        tasks_per_employee_per_month=case.tasks_per_employee_per_month,
        expected_time_reduction_percent=case.expected_time_reduction_percent,
        monthly_ai_cost=case.monthly_ai_cost,
        implementation_cost=case.implementation_cost,
        current_monthly_cost=case.current_monthly_cost,
        estimated_new_labor_cost=case.estimated_new_labor_cost,
        estimated_new_total_cost=case.estimated_new_total_cost,
        monthly_savings=case.monthly_savings,
        annual_savings=case.annual_savings,
        estimated_first_year_roi_percent=case.estimated_first_year_roi_percent,
        payback_period_months=case.payback_period_months,
        recommended_deployment=case.recommended_deployment,
        deployment_rationale=case.deployment_rationale,
        assumptions=case.assumptions,
        scenario_is_estimate=True,
        status=case.status,
        review_notes=case.review_notes,
        reviewed_at=case.reviewed_at,
        created_at=case.created_at,
        updated_at=case.updated_at,
        deployment_assessments=[
            serialize_assessment(assessment) for assessment in case.deployment_assessments
        ],
        brief=serialize_brief(case.brief),
        poc_plan=serialize_plan(case.poc_plan),
    )


def handle_error(exc: Exception) -> HTTPException:
    if isinstance(exc, accounts_service.AccountNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if isinstance(exc, service.BusinessCaseNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(
        exc,
        (
            service.BusinessCaseConflictError,
            service.BusinessCasePrerequisiteError,
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


@router.get(
    "/accounts/{account_id}/business-case", response_model=BusinessCaseWorkspaceResponse
)
def get_business_case(
    account_id: uuid.UUID, session: SessionDep
) -> BusinessCaseWorkspaceResponse:
    try:
        account, case, business_state, deployment_state, evaluation_completed = (
            service.get_workspace(session, account_id)
        )
        return BusinessCaseWorkspaceResponse(
            account_id=account_id,
            current_stage=account.current_stage,
            business_case_stage_status=business_state.status,
            deployment_stage_status=deployment_state.status,
            evaluation_completed=evaluation_completed,
            case=serialize_case(case) if case is not None else None,
        )
    except Exception as exc:
        raise handle_error(exc) from exc


@router.post(
    "/accounts/{account_id}/business-cases/generate",
    response_model=BusinessCaseResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_business_case(account_id: uuid.UUID, session: SessionDep) -> BusinessCaseResponse:
    try:
        return serialize_case(service.generate_case(session, account_id))
    except Exception as exc:
        raise handle_error(exc) from exc


@router.patch(
    "/business-cases/{case_id}/scenario", response_model=BusinessCaseResponse
)
def patch_scenario(
    case_id: uuid.UUID, payload: RoiScenarioUpdate, session: SessionDep
) -> BusinessCaseResponse:
    try:
        return serialize_case(service.update_scenario(session, case_id, payload))
    except Exception as exc:
        raise handle_error(exc) from exc


@router.patch(
    "/business-cases/{case_id}/deployment", response_model=BusinessCaseResponse
)
def patch_deployment(
    case_id: uuid.UUID,
    payload: DeploymentRecommendationUpdate,
    session: SessionDep,
) -> BusinessCaseResponse:
    try:
        return serialize_case(service.update_deployment(session, case_id, payload))
    except Exception as exc:
        raise handle_error(exc) from exc


@router.patch("/account-briefs/{brief_id}", response_model=BusinessCaseResponse)
def patch_account_brief(
    brief_id: uuid.UUID, payload: AccountBriefUpdate, session: SessionDep
) -> BusinessCaseResponse:
    try:
        return serialize_case(service.update_brief(session, brief_id, payload))
    except Exception as exc:
        raise handle_error(exc) from exc


@router.post(
    "/business-cases/{case_id}/review", response_model=BusinessCaseResponse
)
def post_business_case_review(
    case_id: uuid.UUID,
    payload: BusinessCaseReviewRequest,
    session: SessionDep,
) -> BusinessCaseResponse:
    try:
        return serialize_case(service.review_case(session, case_id, payload))
    except Exception as exc:
        raise handle_error(exc) from exc
