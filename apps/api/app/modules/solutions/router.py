import uuid

from fastapi import APIRouter, HTTPException, status

from app.db.session import SessionDep
from app.modules.accounts import service as accounts_service
from app.modules.discovery.models import ConfirmedNeed
from app.modules.solutions import service
from app.modules.solutions.models import SolutionMatch, SolutionProposal, SolutionTemplate
from app.modules.solutions.schemas import (
    NeedSummaryResponse,
    SolutionMatchRequest,
    SolutionMatchResponse,
    SolutionProposalCreate,
    SolutionProposalResponse,
    SolutionProposalUpdate,
    SolutionReviewRequest,
    SolutionTemplateResponse,
    SolutionWorkspaceResponse,
)

router = APIRouter(tags=["solutions"])


def serialize_need(need: ConfirmedNeed) -> NeedSummaryResponse:
    return NeedSummaryResponse(
        id=need.id,
        title=need.title,
        description=need.description,
        business_impact=need.business_impact,
        success_metric=need.success_metric,
        constraints=need.constraints,
        confirmed_at=need.confirmed_at,
    )


def serialize_template(template: SolutionTemplate) -> SolutionTemplateResponse:
    return SolutionTemplateResponse(
        id=template.id,
        slug=template.slug,
        name=template.name,
        description=template.description,
        target_pain_points=template.target_pain_points,
        target_industries=template.target_industries,
        required_data=template.required_data,
        architecture=template.architecture,
        deployment_options=template.deployment_options,
        success_metrics=template.success_metrics,
        known_limitations=template.known_limitations,
        estimated_cost_model=template.estimated_cost_model,
        example_use_cases=template.example_use_cases,
        is_simulated=template.is_simulated,
        version=template.version,
    )


def serialize_match(match: SolutionMatch) -> SolutionMatchResponse:
    return SolutionMatchResponse(
        id=match.id,
        confirmed_need_id=match.confirmed_need_id,
        score=match.score,
        rationale=match.rationale,
        matched_terms=match.matched_terms,
        created_at=match.created_at,
        template=serialize_template(match.solution_template),
    )


def serialize_proposal(proposal: SolutionProposal) -> SolutionProposalResponse:
    return SolutionProposalResponse(
        id=proposal.id,
        account_id=proposal.account_id,
        title=proposal.title,
        executive_summary=proposal.executive_summary,
        why_fit=proposal.why_fit,
        architecture=proposal.architecture,
        required_data=proposal.required_data,
        model_tool_requirements=proposal.model_tool_requirements,
        deployment_option=proposal.deployment_option,
        security_considerations=proposal.security_considerations,
        risks=proposal.risks,
        expected_business_impact=proposal.expected_business_impact,
        success_metrics=proposal.success_metrics,
        status=proposal.status,
        review_notes=proposal.review_notes,
        reviewed_at=proposal.reviewed_at,
        created_at=proposal.created_at,
        updated_at=proposal.updated_at,
        template=serialize_template(proposal.solution_template),
        derived_needs=[serialize_need(need) for need in proposal.derived_needs],
    )


def serialize_workspace(account_id: uuid.UUID, session: SessionDep) -> SolutionWorkspaceResponse:
    account, catalog, needs, matches, proposals, discovery_approved = (
        service.get_solution_workspace(session, account_id)
    )
    return SolutionWorkspaceResponse(
        account_id=account_id,
        current_stage=account.current_stage,
        discovery_approved=discovery_approved,
        catalog_is_simulated=True,
        catalog=[serialize_template(template) for template in catalog],
        confirmed_needs=[serialize_need(need) for need in needs],
        matches=[serialize_match(match) for match in matches],
        proposals=[serialize_proposal(proposal) for proposal in proposals],
    )


def handle_error(exc: Exception) -> HTTPException:
    if isinstance(exc, accounts_service.AccountNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if isinstance(exc, service.SolutionNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(
        exc,
        (
            service.SolutionConflictError,
            service.SolutionPrerequisiteError,
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


@router.get("/solutions/catalog", response_model=list[SolutionTemplateResponse])
def get_solution_catalog(session: SessionDep) -> list[SolutionTemplateResponse]:
    return [serialize_template(template) for template in service.ensure_catalog(session)]


@router.get("/accounts/{account_id}/solutions", response_model=SolutionWorkspaceResponse)
def get_solutions(account_id: uuid.UUID, session: SessionDep) -> SolutionWorkspaceResponse:
    try:
        return serialize_workspace(account_id, session)
    except Exception as exc:
        raise handle_error(exc) from exc


@router.post(
    "/accounts/{account_id}/solutions/matches",
    response_model=list[SolutionMatchResponse],
    status_code=status.HTTP_201_CREATED,
)
def post_solution_matches(
    account_id: uuid.UUID,
    payload: SolutionMatchRequest,
    session: SessionDep,
) -> list[SolutionMatchResponse]:
    try:
        return [
            serialize_match(match)
            for match in service.generate_matches(session, account_id, payload)
        ]
    except Exception as exc:
        raise handle_error(exc) from exc


@router.post(
    "/accounts/{account_id}/solution-proposals",
    response_model=SolutionProposalResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_solution_proposal(
    account_id: uuid.UUID,
    payload: SolutionProposalCreate,
    session: SessionDep,
) -> SolutionProposalResponse:
    try:
        return serialize_proposal(service.create_proposal(session, account_id, payload))
    except Exception as exc:
        raise handle_error(exc) from exc


@router.patch("/solution-proposals/{proposal_id}", response_model=SolutionProposalResponse)
def patch_solution_proposal(
    proposal_id: uuid.UUID,
    payload: SolutionProposalUpdate,
    session: SessionDep,
) -> SolutionProposalResponse:
    try:
        return serialize_proposal(service.update_proposal(session, proposal_id, payload))
    except Exception as exc:
        raise handle_error(exc) from exc


@router.post("/solution-proposals/{proposal_id}/review", response_model=SolutionProposalResponse)
def post_solution_review(
    proposal_id: uuid.UUID,
    payload: SolutionReviewRequest,
    session: SessionDep,
) -> SolutionProposalResponse:
    try:
        return serialize_proposal(service.review_proposal(session, proposal_id, payload))
    except Exception as exc:
        raise handle_error(exc) from exc
