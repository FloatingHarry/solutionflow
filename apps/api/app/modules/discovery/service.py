import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.accounts import service as accounts_service
from app.modules.accounts.enums import StageName, StageStatus
from app.modules.accounts.schemas import WorkflowTransitionRequest
from app.modules.discovery.enums import (
    HypothesisOrigin,
    HypothesisReviewDecision,
    HypothesisStatus,
)
from app.modules.discovery.models import (
    ConfirmedNeed,
    CustomerAnswer,
    DiscoveryQuestion,
    DiscoveryReview,
    OpportunityHypothesis,
)
from app.modules.discovery.schemas import (
    ConfirmedNeedCreate,
    CustomerAnswerCreate,
    CustomerAnswerUpdate,
    DiscoveryGenerateRequest,
    DiscoveryQuestionCreate,
    DiscoveryQuestionUpdate,
    DiscoveryReviewRequest,
    HypothesisCreate,
    HypothesisReviewRequest,
)
from app.modules.research.enums import (
    ClaimReviewStatus,
    ProfileSection,
    ResearchStatus,
    ReviewDecision,
)
from app.modules.research.models import CompanyProfile, Evidence, ProfileClaim, ResearchRun


class DiscoveryNotFoundError(Exception):
    pass


class DiscoveryConflictError(Exception):
    pass


class DiscoveryPrerequisiteError(Exception):
    pass


class ArchivedAccountError(Exception):
    pass


SECTION_LABELS: dict[ProfileSection, str] = {
    ProfileSection.COMPANY_OVERVIEW: "company context",
    ProfileSection.PRODUCTS_SERVICES: "products and services",
    ProfileSection.MARKET_GEOGRAPHY: "markets and geography",
    ProfileSection.CUSTOMERS: "customer operations",
    ProfileSection.RECENT_DEVELOPMENTS: "recent developments",
    ProfileSection.FINANCIAL_OPERATING_SIGNALS: "financial and operating signals",
    ProfileSection.AI_DIGITAL_INITIATIVES: "AI and digital initiatives",
    ProfileSection.POTENTIAL_STRATEGIC_PRIORITIES: "strategic priorities",
}


def utc_now() -> datetime:
    return datetime.now(UTC)


def _ensure_editable(session: Session, account_id: uuid.UUID) -> None:
    account = accounts_service.get_account_or_raise(session, account_id)
    if account.archived_at is not None:
        raise ArchivedAccountError


def _ensure_discovery_editable(session: Session, account_id: uuid.UUID) -> None:
    if _workflow_state(session, account_id, StageName.DISCOVERY).status == StageStatus.COMPLETED:
        raise DiscoveryConflictError("Approved customer discovery is read-only")


def _workflow_state(session: Session, account_id: uuid.UUID, stage: StageName):
    _account, stages = accounts_service.get_workflow(session, account_id)
    return next(state for state in stages if state.stage == stage)


def _require_research_approved(session: Session, account_id: uuid.UUID) -> None:
    if _workflow_state(session, account_id, StageName.RESEARCH).status != StageStatus.COMPLETED:
        raise DiscoveryPrerequisiteError(
            "Approve account research before creating opportunity hypotheses"
        )


def _ensure_opportunity_started(session: Session, account_id: uuid.UUID) -> None:
    state = _workflow_state(session, account_id, StageName.OPPORTUNITY)
    if state.status in {StageStatus.NOT_STARTED, StageStatus.BLOCKED}:
        accounts_service.transition_workflow(
            session,
            account_id,
            WorkflowTransitionRequest(
                stage=StageName.OPPORTUNITY,
                status=StageStatus.IN_PROGRESS,
                reason="Opportunity hypothesis work started",
            ),
        )


def _start_discovery_after_acceptance(session: Session, account_id: uuid.UUID) -> None:
    opportunity = _workflow_state(session, account_id, StageName.OPPORTUNITY)
    if opportunity.status in {StageStatus.IN_PROGRESS, StageStatus.BLOCKED}:
        accounts_service.transition_workflow(
            session,
            account_id,
            WorkflowTransitionRequest(
                stage=StageName.OPPORTUNITY,
                status=StageStatus.COMPLETED,
                reason="An opportunity hypothesis was accepted for customer discovery",
            ),
        )

    discovery = _workflow_state(session, account_id, StageName.DISCOVERY)
    if discovery.status in {StageStatus.NOT_STARTED, StageStatus.BLOCKED}:
        accounts_service.transition_workflow(
            session,
            account_id,
            WorkflowTransitionRequest(
                stage=StageName.DISCOVERY,
                status=StageStatus.IN_PROGRESS,
                reason="Customer discovery started from an accepted hypothesis",
            ),
        )


def _hypothesis_options():
    return (
        selectinload(OpportunityHypothesis.evidence_items).selectinload(Evidence.source),
        selectinload(OpportunityHypothesis.questions).selectinload(DiscoveryQuestion.answers),
        selectinload(OpportunityHypothesis.confirmed_need).selectinload(
            ConfirmedNeed.supporting_answers
        ),
    )


def get_hypothesis_or_raise(session: Session, hypothesis_id: uuid.UUID) -> OpportunityHypothesis:
    hypothesis = session.scalar(
        select(OpportunityHypothesis)
        .where(OpportunityHypothesis.id == hypothesis_id)
        .options(*_hypothesis_options())
    )
    if hypothesis is None:
        raise DiscoveryNotFoundError("Opportunity hypothesis not found")
    return hypothesis


def get_question_or_raise(session: Session, question_id: uuid.UUID) -> DiscoveryQuestion:
    question = session.scalar(
        select(DiscoveryQuestion)
        .where(DiscoveryQuestion.id == question_id)
        .options(
            selectinload(DiscoveryQuestion.answers),
            selectinload(DiscoveryQuestion.hypothesis),
        )
    )
    if question is None:
        raise DiscoveryNotFoundError("Discovery question not found")
    return question


def get_answer_or_raise(session: Session, answer_id: uuid.UUID) -> CustomerAnswer:
    answer = session.get(CustomerAnswer, answer_id)
    if answer is None:
        raise DiscoveryNotFoundError("Customer answer not found")
    return answer


def get_discovery_workspace(
    session: Session, account_id: uuid.UUID
) -> tuple[
    list[OpportunityHypothesis],
    list[ConfirmedNeed],
    list[DiscoveryReview],
    StageName,
    bool,
]:
    account = accounts_service.get_account_or_raise(session, account_id)
    hypotheses = list(
        session.scalars(
            select(OpportunityHypothesis)
            .where(OpportunityHypothesis.account_id == account_id)
            .options(*_hypothesis_options())
            .order_by(OpportunityHypothesis.created_at.desc())
        ).all()
    )
    needs = list(
        session.scalars(
            select(ConfirmedNeed)
            .where(ConfirmedNeed.account_id == account_id)
            .options(selectinload(ConfirmedNeed.supporting_answers))
            .order_by(ConfirmedNeed.confirmed_at.desc())
        ).all()
    )
    reviews = list(
        session.scalars(
            select(DiscoveryReview)
            .where(DiscoveryReview.account_id == account_id)
            .order_by(DiscoveryReview.created_at.desc())
        ).all()
    )
    research_approved = (
        _workflow_state(session, account_id, StageName.RESEARCH).status == StageStatus.COMPLETED
    )
    return hypotheses, needs, reviews, account.current_stage, research_approved


def create_hypothesis(
    session: Session, account_id: uuid.UUID, payload: HypothesisCreate
) -> OpportunityHypothesis:
    _ensure_editable(session, account_id)
    _ensure_discovery_editable(session, account_id)
    _require_research_approved(session, account_id)

    evidence_items: list[Evidence] = []
    if payload.evidence_ids:
        evidence_items = list(
            session.scalars(
                select(Evidence).where(
                    Evidence.id.in_(payload.evidence_ids), Evidence.account_id == account_id
                )
            ).all()
        )
        if len(evidence_items) != len(set(payload.evidence_ids)):
            raise DiscoveryConflictError("One or more evidence records are invalid")

    _ensure_opportunity_started(session, account_id)

    hypothesis = OpportunityHypothesis(
        account_id=account_id,
        title=payload.title,
        description=payload.description,
        confidence=payload.confidence,
        business_area=payload.business_area,
        potential_impact=payload.potential_impact,
        status=HypothesisStatus.NEED_VALIDATION,
        origin=HypothesisOrigin.MANUAL,
    )
    hypothesis.evidence_items.extend(evidence_items)
    session.add(hypothesis)
    session.flush()
    accounts_service.add_activity(
        session,
        account_id=account_id,
        event_type="discovery.hypothesis_created",
        entity_type="opportunity_hypothesis",
        entity_id=str(hypothesis.id),
        summary=f"Opportunity hypothesis created: {hypothesis.title}",
        metadata={"origin": hypothesis.origin.value},
    )
    session.commit()
    return get_hypothesis_or_raise(session, hypothesis.id)


def _latest_approved_profile(session: Session, account_id: uuid.UUID) -> CompanyProfile | None:
    return session.scalar(
        select(CompanyProfile)
        .join(ResearchRun, CompanyProfile.research_run_id == ResearchRun.id)
        .where(
            CompanyProfile.account_id == account_id,
            ResearchRun.status == ResearchStatus.COMPLETED,
        )
        .options(
            selectinload(CompanyProfile.claims)
            .selectinload(ProfileClaim.evidence_items)
            .selectinload(Evidence.source)
        )
        .order_by(CompanyProfile.created_at.desc())
    )


def _starter_questions(area: str) -> list[tuple[str, str]]:
    return [
        (
            f"How does {area} work today, and which people or systems are involved?",
            "Establish the current workflow before proposing change.",
        ),
        (
            "What measurable cost, delay, risk, or quality issue occurs in the current process?",
            "Turn the hypothesis into a quantified customer problem.",
        ),
        (
            "Which data, security, compliance, budget, or timeline constraints must be respected?",
            "Capture the boundaries that any viable solution must satisfy.",
        ),
        (
            "What measurable outcome would make this initiative successful?",
            "Define a success metric that can later drive POC evaluation.",
        ),
    ]


def generate_from_research(
    session: Session, account_id: uuid.UUID, payload: DiscoveryGenerateRequest
) -> list[OpportunityHypothesis]:
    _ensure_editable(session, account_id)
    _ensure_discovery_editable(session, account_id)
    _require_research_approved(session, account_id)
    profile = _latest_approved_profile(session, account_id)
    if profile is None:
        raise DiscoveryPrerequisiteError("No approved company profile is available")

    existing_claim_ids = set(
        session.scalars(
            select(OpportunityHypothesis.source_claim_id).where(
                OpportunityHypothesis.account_id == account_id,
                OpportunityHypothesis.source_claim_id.is_not(None),
            )
        ).all()
    )
    claims = [
        claim
        for claim in profile.claims
        if claim.review_status == ClaimReviewStatus.HUMAN_REVIEWED
        and claim.evidence_items
        and claim.id not in existing_claim_ids
    ][: payload.max_hypotheses]
    if not claims:
        raise DiscoveryConflictError(
            "No new approved research claims are available for hypothesis generation"
        )

    _ensure_opportunity_started(session, account_id)
    created_ids: list[uuid.UUID] = []
    for claim in claims:
        area = SECTION_LABELS[claim.section]
        hypothesis = OpportunityHypothesis(
            account_id=account_id,
            source_claim_id=claim.id,
            title=f"Validate a measurable opportunity in {area}",
            description=(
                f"Research signal to validate: {claim.statement} This is a hypothesis, "
                "not a confirmed customer need."
            ),
            confidence=claim.confidence,
            business_area=area.title(),
            potential_impact=(
                "Potential impact is unknown and must be quantified through customer answers."
            ),
            status=HypothesisStatus.NEED_VALIDATION,
            origin=HypothesisOrigin.RESEARCH_TEMPLATE,
        )
        hypothesis.evidence_items.extend(claim.evidence_items)
        for position, (question, rationale) in enumerate(_starter_questions(area)):
            hypothesis.questions.append(
                DiscoveryQuestion(
                    account_id=account_id,
                    question=question,
                    rationale=rationale,
                    position=position,
                )
            )
        session.add(hypothesis)
        session.flush()
        created_ids.append(hypothesis.id)

    accounts_service.add_activity(
        session,
        account_id=account_id,
        event_type="discovery.hypotheses_generated",
        entity_type="opportunity_hypothesis",
        summary=f"Generated {len(created_ids)} research-grounded opportunity hypotheses",
        metadata={"count": len(created_ids), "method": "research_template"},
    )
    session.commit()
    return [get_hypothesis_or_raise(session, item_id) for item_id in created_ids]


def review_hypothesis(
    session: Session, hypothesis_id: uuid.UUID, payload: HypothesisReviewRequest
) -> OpportunityHypothesis:
    hypothesis = get_hypothesis_or_raise(session, hypothesis_id)
    _ensure_editable(session, hypothesis.account_id)
    _ensure_discovery_editable(session, hypothesis.account_id)
    if hypothesis.status == HypothesisStatus.CONFIRMED:
        raise DiscoveryConflictError("A confirmed hypothesis cannot be reviewed again")

    status_by_decision = {
        HypothesisReviewDecision.ACCEPT: HypothesisStatus.USER_ACCEPTED,
        HypothesisReviewDecision.REJECT: HypothesisStatus.USER_REJECTED,
        HypothesisReviewDecision.NEED_VALIDATION: HypothesisStatus.NEED_VALIDATION,
    }
    hypothesis.status = status_by_decision[payload.decision]
    hypothesis.review_notes = payload.notes
    hypothesis.reviewed_at = utc_now()
    hypothesis.updated_at = hypothesis.reviewed_at
    accounts_service.add_activity(
        session,
        account_id=hypothesis.account_id,
        event_type="discovery.hypothesis_reviewed",
        entity_type="opportunity_hypothesis",
        entity_id=str(hypothesis.id),
        summary=f"Hypothesis marked {hypothesis.status.value.replace('_', ' ')}",
        metadata={"decision": payload.decision.value, "notes": payload.notes},
    )
    session.commit()

    if payload.decision == HypothesisReviewDecision.ACCEPT:
        _start_discovery_after_acceptance(session, hypothesis.account_id)
    return get_hypothesis_or_raise(session, hypothesis.id)


def create_question(
    session: Session, hypothesis_id: uuid.UUID, payload: DiscoveryQuestionCreate
) -> DiscoveryQuestion:
    hypothesis = get_hypothesis_or_raise(session, hypothesis_id)
    _ensure_editable(session, hypothesis.account_id)
    _ensure_discovery_editable(session, hypothesis.account_id)
    if hypothesis.status == HypothesisStatus.USER_REJECTED:
        raise DiscoveryConflictError("Questions cannot be added to a rejected hypothesis")
    question = DiscoveryQuestion(
        account_id=hypothesis.account_id,
        hypothesis_id=hypothesis.id,
        question=payload.question,
        rationale=payload.rationale,
        position=len(hypothesis.questions),
    )
    session.add(question)
    session.flush()
    accounts_service.add_activity(
        session,
        account_id=hypothesis.account_id,
        event_type="discovery.question_created",
        entity_type="discovery_question",
        entity_id=str(question.id),
        summary="Discovery question added",
        metadata={"hypothesis_id": str(hypothesis.id)},
    )
    session.commit()
    session.refresh(question)
    return question


def update_question(
    session: Session, question_id: uuid.UUID, payload: DiscoveryQuestionUpdate
) -> DiscoveryQuestion:
    question = get_question_or_raise(session, question_id)
    _ensure_editable(session, question.account_id)
    _ensure_discovery_editable(session, question.account_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(question, field, value)
    question.updated_at = utc_now()
    accounts_service.add_activity(
        session,
        account_id=question.account_id,
        event_type="discovery.question_updated",
        entity_type="discovery_question",
        entity_id=str(question.id),
        summary="Discovery question updated",
    )
    session.commit()
    session.refresh(question)
    return question


def delete_question(session: Session, question_id: uuid.UUID) -> None:
    question = get_question_or_raise(session, question_id)
    _ensure_editable(session, question.account_id)
    _ensure_discovery_editable(session, question.account_id)
    if question.answers:
        raise DiscoveryConflictError("Answered questions cannot be deleted")
    account_id = question.account_id
    session.delete(question)
    accounts_service.add_activity(
        session,
        account_id=account_id,
        event_type="discovery.question_deleted",
        entity_type="discovery_question",
        entity_id=str(question_id),
        summary="Unanswered discovery question deleted",
    )
    session.commit()


def create_answer(
    session: Session, question_id: uuid.UUID, payload: CustomerAnswerCreate
) -> CustomerAnswer:
    question = get_question_or_raise(session, question_id)
    _ensure_editable(session, question.account_id)
    _ensure_discovery_editable(session, question.account_id)
    if question.hypothesis.status != HypothesisStatus.USER_ACCEPTED:
        raise DiscoveryConflictError("Accept the hypothesis before recording customer answers")
    answer = CustomerAnswer(
        account_id=question.account_id,
        question_id=question.id,
        answer_text=payload.answer_text,
        respondent_name=payload.respondent_name,
        respondent_role=payload.respondent_role,
    )
    session.add(answer)
    session.flush()
    accounts_service.add_activity(
        session,
        account_id=question.account_id,
        event_type="discovery.answer_recorded",
        entity_type="customer_answer",
        entity_id=str(answer.id),
        summary="Customer answer recorded",
        metadata={"question_id": str(question.id)},
    )
    session.commit()
    session.refresh(answer)
    return answer


def update_answer(
    session: Session, answer_id: uuid.UUID, payload: CustomerAnswerUpdate
) -> CustomerAnswer:
    answer = get_answer_or_raise(session, answer_id)
    _ensure_editable(session, answer.account_id)
    _ensure_discovery_editable(session, answer.account_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(answer, field, value)
    answer.updated_at = utc_now()
    accounts_service.add_activity(
        session,
        account_id=answer.account_id,
        event_type="discovery.answer_updated",
        entity_type="customer_answer",
        entity_id=str(answer.id),
        summary="Customer answer updated",
    )
    session.commit()
    session.refresh(answer)
    return answer


def confirm_need(
    session: Session, hypothesis_id: uuid.UUID, payload: ConfirmedNeedCreate
) -> ConfirmedNeed:
    hypothesis = get_hypothesis_or_raise(session, hypothesis_id)
    _ensure_editable(session, hypothesis.account_id)
    _ensure_discovery_editable(session, hypothesis.account_id)
    if hypothesis.status != HypothesisStatus.USER_ACCEPTED:
        raise DiscoveryConflictError("Only an accepted hypothesis can become a confirmed need")
    if hypothesis.confirmed_need is not None:
        raise DiscoveryConflictError("This hypothesis already has a confirmed need")

    answers = [answer for question in hypothesis.questions for answer in question.answers]
    if not answers:
        raise DiscoveryConflictError("Record at least one customer answer first")
    answer_by_id = {answer.id: answer for answer in answers}
    requested_ids = set(payload.answer_ids)
    if requested_ids and not requested_ids.issubset(answer_by_id):
        raise DiscoveryConflictError("Supporting answers must belong to this hypothesis")
    supporting_answers = (
        [answer_by_id[answer_id] for answer_id in payload.answer_ids]
        if payload.answer_ids
        else answers
    )

    need = ConfirmedNeed(
        account_id=hypothesis.account_id,
        hypothesis_id=hypothesis.id,
        title=payload.title,
        description=payload.description,
        business_impact=payload.business_impact,
        success_metric=payload.success_metric,
        constraints=payload.constraints,
    )
    need.supporting_answers.extend(supporting_answers)
    hypothesis.status = HypothesisStatus.CONFIRMED
    hypothesis.updated_at = utc_now()
    session.add(need)
    session.flush()
    accounts_service.add_activity(
        session,
        account_id=hypothesis.account_id,
        event_type="discovery.need_confirmed",
        entity_type="confirmed_need",
        entity_id=str(need.id),
        summary=f"Customer need confirmed: {need.title}",
        metadata={
            "hypothesis_id": str(hypothesis.id),
            "supporting_answer_count": len(supporting_answers),
        },
    )
    session.commit()
    confirmed_need = session.scalar(
        select(ConfirmedNeed)
        .where(ConfirmedNeed.id == need.id)
        .options(selectinload(ConfirmedNeed.supporting_answers))
    )
    if confirmed_need is None:
        raise DiscoveryConflictError("Confirmed need could not be loaded")
    return confirmed_need


def review_discovery(
    session: Session, account_id: uuid.UUID, payload: DiscoveryReviewRequest
) -> DiscoveryReview:
    _ensure_editable(session, account_id)
    discovery = _workflow_state(session, account_id, StageName.DISCOVERY)
    if discovery.status not in {StageStatus.IN_PROGRESS, StageStatus.BLOCKED}:
        raise DiscoveryConflictError("Customer discovery is not awaiting review")
    if payload.decision == ReviewDecision.REJECT and discovery.status == StageStatus.BLOCKED:
        raise DiscoveryConflictError("Customer discovery already needs revision")
    if payload.decision == ReviewDecision.APPROVE:
        need = session.scalar(
            select(ConfirmedNeed.id).where(ConfirmedNeed.account_id == account_id).limit(1)
        )
        if need is None:
            raise DiscoveryConflictError("Confirm at least one customer need before approval")

    review = DiscoveryReview(
        account_id=account_id,
        decision=payload.decision,
        notes=payload.notes,
    )
    session.add(review)
    session.flush()
    event_type = (
        "discovery.approved" if payload.decision == ReviewDecision.APPROVE else "discovery.rejected"
    )
    accounts_service.add_activity(
        session,
        account_id=account_id,
        event_type=event_type,
        entity_type="discovery_review",
        entity_id=str(review.id),
        summary=(
            "Customer discovery approved"
            if payload.decision == ReviewDecision.APPROVE
            else "Customer discovery needs revision"
        ),
        metadata={"notes": payload.notes},
    )
    session.commit()
    session.refresh(review)

    accounts_service.transition_workflow(
        session,
        account_id,
        WorkflowTransitionRequest(
            stage=StageName.DISCOVERY,
            status=(
                StageStatus.COMPLETED
                if payload.decision == ReviewDecision.APPROVE
                else StageStatus.BLOCKED
            ),
            reason=payload.notes,
        ),
    )
    return review
