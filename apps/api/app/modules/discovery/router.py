import uuid

from fastapi import APIRouter, HTTPException, Response, status

from app.db.session import SessionDep
from app.modules.accounts import service as accounts_service
from app.modules.discovery import service
from app.modules.discovery.models import ConfirmedNeed, DiscoveryQuestion, OpportunityHypothesis
from app.modules.discovery.schemas import (
    ConfirmedNeedCreate,
    ConfirmedNeedResponse,
    CustomerAnswerCreate,
    CustomerAnswerResponse,
    CustomerAnswerUpdate,
    DiscoveryGenerateRequest,
    DiscoveryQuestionCreate,
    DiscoveryQuestionResponse,
    DiscoveryQuestionUpdate,
    DiscoveryReviewRequest,
    DiscoveryReviewResponse,
    DiscoveryWorkspaceResponse,
    HypothesisCreate,
    HypothesisReviewRequest,
    OpportunityHypothesisResponse,
)
from app.modules.research.models import Evidence
from app.modules.research.schemas import CitationResponse

router = APIRouter(tags=["discovery"])


def serialize_evidence(evidence: Evidence) -> CitationResponse:
    return CitationResponse(
        evidence_id=evidence.id,
        source_id=evidence.source.id,
        source_title=evidence.source.title,
        source_url=evidence.source.url,
        publisher=evidence.source.publisher,
        supporting_text=evidence.supporting_text,
        locator=evidence.locator,
        confidence=evidence.confidence,
        verification_status=evidence.verification_status,
        retrieved_at=evidence.source.retrieved_at,
    )


def serialize_question(question: DiscoveryQuestion) -> DiscoveryQuestionResponse:
    return DiscoveryQuestionResponse(
        id=question.id,
        hypothesis_id=question.hypothesis_id,
        question=question.question,
        rationale=question.rationale,
        position=question.position,
        created_at=question.created_at,
        updated_at=question.updated_at,
        answers=[CustomerAnswerResponse.model_validate(answer) for answer in question.answers],
    )


def serialize_need(need: ConfirmedNeed | None) -> ConfirmedNeedResponse | None:
    if need is None:
        return None
    return ConfirmedNeedResponse(
        id=need.id,
        hypothesis_id=need.hypothesis_id,
        title=need.title,
        description=need.description,
        business_impact=need.business_impact,
        success_metric=need.success_metric,
        constraints=need.constraints,
        confirmed_at=need.confirmed_at,
        supporting_answer_ids=[answer.id for answer in need.supporting_answers],
    )


def serialize_hypothesis(hypothesis: OpportunityHypothesis) -> OpportunityHypothesisResponse:
    return OpportunityHypothesisResponse(
        id=hypothesis.id,
        account_id=hypothesis.account_id,
        source_claim_id=hypothesis.source_claim_id,
        title=hypothesis.title,
        description=hypothesis.description,
        confidence=hypothesis.confidence,
        business_area=hypothesis.business_area,
        potential_impact=hypothesis.potential_impact,
        status=hypothesis.status,
        origin=hypothesis.origin,
        review_notes=hypothesis.review_notes,
        reviewed_at=hypothesis.reviewed_at,
        created_at=hypothesis.created_at,
        updated_at=hypothesis.updated_at,
        evidence=[serialize_evidence(evidence) for evidence in hypothesis.evidence_items],
        questions=[serialize_question(question) for question in hypothesis.questions],
        confirmed_need=serialize_need(hypothesis.confirmed_need),
    )


def serialize_workspace(account_id: uuid.UUID, session: SessionDep) -> DiscoveryWorkspaceResponse:
    hypotheses, needs, reviews, current_stage, research_approved = service.get_discovery_workspace(
        session, account_id
    )
    return DiscoveryWorkspaceResponse(
        account_id=account_id,
        current_stage=current_stage,
        research_approved=research_approved,
        hypotheses=[serialize_hypothesis(hypothesis) for hypothesis in hypotheses],
        confirmed_needs=[serialize_need(need) for need in needs if need is not None],
        reviews=[DiscoveryReviewResponse.model_validate(review) for review in reviews],
    )


def handle_error(exc: Exception) -> HTTPException:
    if isinstance(exc, accounts_service.AccountNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if isinstance(exc, service.DiscoveryNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(
        exc,
        (
            service.DiscoveryConflictError,
            service.DiscoveryPrerequisiteError,
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


@router.get("/accounts/{account_id}/discovery", response_model=DiscoveryWorkspaceResponse)
def get_discovery(account_id: uuid.UUID, session: SessionDep) -> DiscoveryWorkspaceResponse:
    try:
        return serialize_workspace(account_id, session)
    except Exception as exc:
        raise handle_error(exc) from exc


@router.post(
    "/accounts/{account_id}/discovery/generate",
    response_model=list[OpportunityHypothesisResponse],
    status_code=status.HTTP_201_CREATED,
)
def generate_discovery(
    account_id: uuid.UUID,
    payload: DiscoveryGenerateRequest,
    session: SessionDep,
) -> list[OpportunityHypothesisResponse]:
    try:
        hypotheses = service.generate_from_research(session, account_id, payload)
        return [serialize_hypothesis(hypothesis) for hypothesis in hypotheses]
    except Exception as exc:
        raise handle_error(exc) from exc


@router.post(
    "/accounts/{account_id}/opportunity-hypotheses",
    response_model=OpportunityHypothesisResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_hypothesis(
    account_id: uuid.UUID, payload: HypothesisCreate, session: SessionDep
) -> OpportunityHypothesisResponse:
    try:
        return serialize_hypothesis(service.create_hypothesis(session, account_id, payload))
    except Exception as exc:
        raise handle_error(exc) from exc


@router.post(
    "/opportunity-hypotheses/{hypothesis_id}/review",
    response_model=OpportunityHypothesisResponse,
)
def review_hypothesis(
    hypothesis_id: uuid.UUID,
    payload: HypothesisReviewRequest,
    session: SessionDep,
) -> OpportunityHypothesisResponse:
    try:
        return serialize_hypothesis(service.review_hypothesis(session, hypothesis_id, payload))
    except Exception as exc:
        raise handle_error(exc) from exc


@router.post(
    "/opportunity-hypotheses/{hypothesis_id}/questions",
    response_model=DiscoveryQuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_question(
    hypothesis_id: uuid.UUID,
    payload: DiscoveryQuestionCreate,
    session: SessionDep,
) -> DiscoveryQuestionResponse:
    try:
        question = service.create_question(session, hypothesis_id, payload)
        question = service.get_question_or_raise(session, question.id)
        return serialize_question(question)
    except Exception as exc:
        raise handle_error(exc) from exc


@router.patch("/discovery-questions/{question_id}", response_model=DiscoveryQuestionResponse)
def patch_question(
    question_id: uuid.UUID,
    payload: DiscoveryQuestionUpdate,
    session: SessionDep,
) -> DiscoveryQuestionResponse:
    try:
        service.update_question(session, question_id, payload)
        return serialize_question(service.get_question_or_raise(session, question_id))
    except Exception as exc:
        raise handle_error(exc) from exc


@router.delete("/discovery-questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(question_id: uuid.UUID, session: SessionDep) -> Response:
    try:
        service.delete_question(session, question_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        raise handle_error(exc) from exc


@router.post(
    "/discovery-questions/{question_id}/answers",
    response_model=CustomerAnswerResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_answer(
    question_id: uuid.UUID,
    payload: CustomerAnswerCreate,
    session: SessionDep,
) -> CustomerAnswerResponse:
    try:
        return CustomerAnswerResponse.model_validate(
            service.create_answer(session, question_id, payload)
        )
    except Exception as exc:
        raise handle_error(exc) from exc


@router.patch("/customer-answers/{answer_id}", response_model=CustomerAnswerResponse)
def patch_answer(
    answer_id: uuid.UUID,
    payload: CustomerAnswerUpdate,
    session: SessionDep,
) -> CustomerAnswerResponse:
    try:
        return CustomerAnswerResponse.model_validate(
            service.update_answer(session, answer_id, payload)
        )
    except Exception as exc:
        raise handle_error(exc) from exc


@router.post(
    "/opportunity-hypotheses/{hypothesis_id}/confirm",
    response_model=ConfirmedNeedResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_confirmed_need(
    hypothesis_id: uuid.UUID,
    payload: ConfirmedNeedCreate,
    session: SessionDep,
) -> ConfirmedNeedResponse:
    try:
        need = service.confirm_need(session, hypothesis_id, payload)
        response = serialize_need(need)
        if response is None:
            raise service.DiscoveryConflictError("Confirmed need could not be loaded")
        return response
    except Exception as exc:
        raise handle_error(exc) from exc


@router.post(
    "/accounts/{account_id}/discovery/review",
    response_model=DiscoveryReviewResponse,
)
def post_discovery_review(
    account_id: uuid.UUID,
    payload: DiscoveryReviewRequest,
    session: SessionDep,
) -> DiscoveryReviewResponse:
    try:
        return DiscoveryReviewResponse.model_validate(
            service.review_discovery(session, account_id, payload)
        )
    except Exception as exc:
        raise handle_error(exc) from exc
