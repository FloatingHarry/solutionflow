import re
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.modules.accounts import service as accounts_service
from app.modules.accounts.enums import StageName, StageStatus
from app.modules.accounts.schemas import WorkflowTransitionRequest
from app.modules.discovery.models import ConfirmedNeed
from app.modules.solutions.catalog import DEMO_SOLUTION_CATALOG
from app.modules.solutions.enums import SolutionProposalStatus, SolutionReviewDecision
from app.modules.solutions.models import SolutionMatch, SolutionProposal, SolutionTemplate
from app.modules.solutions.schemas import (
    SolutionMatchRequest,
    SolutionProposalCreate,
    SolutionProposalUpdate,
    SolutionReviewRequest,
)


class SolutionNotFoundError(Exception):
    pass


class SolutionConflictError(Exception):
    pass


class SolutionPrerequisiteError(Exception):
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


def _require_discovery_approved(session: Session, account_id: uuid.UUID) -> None:
    if _workflow_state(session, account_id, StageName.DISCOVERY).status != StageStatus.COMPLETED:
        raise SolutionPrerequisiteError(
            "Approve customer discovery before matching solution templates"
        )


def _ensure_solution_editable(session: Session, account_id: uuid.UUID) -> None:
    if _workflow_state(session, account_id, StageName.SOLUTION).status == StageStatus.COMPLETED:
        raise SolutionConflictError("An accepted solution is read-only")


def _ensure_solution_started(session: Session, account_id: uuid.UUID) -> None:
    state = _workflow_state(session, account_id, StageName.SOLUTION)
    if state.status in {StageStatus.NOT_STARTED, StageStatus.BLOCKED}:
        accounts_service.transition_workflow(
            session,
            account_id,
            WorkflowTransitionRequest(
                stage=StageName.SOLUTION,
                status=StageStatus.IN_PROGRESS,
                reason="Solution matching started from confirmed customer needs",
            ),
        )


def ensure_catalog(session: Session) -> list[SolutionTemplate]:
    existing_slugs = set(session.scalars(select(SolutionTemplate.slug)).all())
    created = False
    for item in DEMO_SOLUTION_CATALOG:
        if item["slug"] in existing_slugs:
            continue
        session.add(SolutionTemplate(**item))
        created = True
    if created:
        session.commit()
    return list(
        session.scalars(
            select(SolutionTemplate)
            .where(SolutionTemplate.is_active.is_(True))
            .order_by(SolutionTemplate.name)
        ).all()
    )


def get_template_or_raise(session: Session, template_id: uuid.UUID) -> SolutionTemplate:
    template = session.get(SolutionTemplate, template_id)
    if template is None or not template.is_active:
        raise SolutionNotFoundError("Solution template not found")
    return template


def get_proposal_or_raise(session: Session, proposal_id: uuid.UUID) -> SolutionProposal:
    proposal = session.scalar(
        select(SolutionProposal)
        .where(SolutionProposal.id == proposal_id)
        .options(
            selectinload(SolutionProposal.solution_template),
            selectinload(SolutionProposal.derived_needs),
        )
    )
    if proposal is None:
        raise SolutionNotFoundError("Solution proposal not found")
    return proposal


def get_solution_workspace(session: Session, account_id: uuid.UUID):
    account = accounts_service.get_account_or_raise(session, account_id)
    catalog = ensure_catalog(session)
    needs = list(
        session.scalars(
            select(ConfirmedNeed)
            .where(ConfirmedNeed.account_id == account_id)
            .order_by(ConfirmedNeed.confirmed_at.desc())
        ).all()
    )
    matches = list(
        session.scalars(
            select(SolutionMatch)
            .where(SolutionMatch.account_id == account_id)
            .options(selectinload(SolutionMatch.solution_template))
            .order_by(SolutionMatch.score.desc(), SolutionMatch.created_at)
        ).all()
    )
    proposals = list(
        session.scalars(
            select(SolutionProposal)
            .where(SolutionProposal.account_id == account_id)
            .options(
                selectinload(SolutionProposal.solution_template),
                selectinload(SolutionProposal.derived_needs),
            )
            .order_by(SolutionProposal.created_at.desc())
        ).all()
    )
    discovery_approved = (
        _workflow_state(session, account_id, StageName.DISCOVERY).status == StageStatus.COMPLETED
    )
    return account, catalog, needs, matches, proposals, discovery_approved


def _normalized_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 2
        and token
        not in {
            "and",
            "the",
            "for",
            "from",
            "with",
            "that",
            "this",
            "into",
            "needs",
            "customer",
        }
    }


def _score_template(need: ConfirmedNeed, template: SolutionTemplate) -> tuple[int, list[str]]:
    need_text = " ".join(
        filter(
            None,
            [
                need.title,
                need.description,
                need.business_impact,
                need.success_metric,
                need.constraints,
            ],
        )
    )
    need_tokens = _normalized_tokens(need_text)
    matched_terms = sorted(
        keyword for keyword in template.match_keywords if _normalized_tokens(keyword) & need_tokens
    )
    score = min(96, 44 + len(matched_terms) * 11)
    if not matched_terms:
        score = 38
    return score, matched_terms


def generate_matches(
    session: Session,
    account_id: uuid.UUID,
    payload: SolutionMatchRequest,
) -> list[SolutionMatch]:
    _ensure_editable(session, account_id)
    _require_discovery_approved(session, account_id)
    _ensure_solution_editable(session, account_id)
    catalog = ensure_catalog(session)
    needs = list(
        session.scalars(select(ConfirmedNeed).where(ConfirmedNeed.account_id == account_id)).all()
    )
    if not needs:
        raise SolutionPrerequisiteError(
            "Confirm at least one customer need before solution matching"
        )

    _ensure_solution_started(session, account_id)
    touched_ids: list[uuid.UUID] = []
    for need in needs:
        ranked = sorted(
            ((_score_template(need, template), template) for template in catalog),
            key=lambda item: (-item[0][0], item[1].name),
        )[: payload.top_per_need]
        for (score, matched_terms), template in ranked:
            match = session.scalar(
                select(SolutionMatch).where(
                    SolutionMatch.confirmed_need_id == need.id,
                    SolutionMatch.solution_template_id == template.id,
                )
            )
            rationale = (
                f"Matched {', '.join(matched_terms)} to the confirmed need. "
                f"The proposal must still be validated against the customer success metric: "
                f"{need.success_metric}"
                if matched_terms
                else (
                    "No direct keyword fit was found. This lower-confidence catalog option "
                    "requires explicit human validation."
                )
            )
            if match is None:
                match = SolutionMatch(
                    account_id=account_id,
                    confirmed_need_id=need.id,
                    solution_template_id=template.id,
                    score=score,
                    rationale=rationale,
                    matched_terms=matched_terms,
                )
                session.add(match)
                session.flush()
            else:
                match.score = score
                match.rationale = rationale
                match.matched_terms = matched_terms
                match.updated_at = utc_now()
            touched_ids.append(match.id)

    accounts_service.add_activity(
        session,
        account_id=account_id,
        event_type="solution.matches_generated",
        entity_type="solution_match",
        summary=f"Generated {len(touched_ids)} solution matches from confirmed needs",
        metadata={"match_count": len(touched_ids), "catalog": "demo_simulated"},
    )
    session.commit()
    return list(
        session.scalars(
            select(SolutionMatch)
            .where(SolutionMatch.id.in_(touched_ids))
            .options(selectinload(SolutionMatch.solution_template))
            .order_by(SolutionMatch.score.desc())
        ).all()
    )


def _load_account_needs(
    session: Session, account_id: uuid.UUID, need_ids: list[uuid.UUID]
) -> list[ConfirmedNeed]:
    needs = list(
        session.scalars(
            select(ConfirmedNeed).where(
                ConfirmedNeed.account_id == account_id,
                ConfirmedNeed.id.in_(need_ids),
            )
        ).all()
    )
    if len(needs) != len(set(need_ids)):
        raise SolutionConflictError("One or more confirmed needs are invalid")
    return needs


def _model_tool_requirements(template: SolutionTemplate) -> list[str]:
    requirements = {
        "enterprise-knowledge-assistant": [
            "embedding and reranking models",
            "grounded language model",
            "access-aware vector and keyword search",
        ],
        "customer-service-copilot": [
            "intent and summarization models",
            "grounded response model",
            "CRM and ticketing connectors",
        ],
        "sales-account-copilot": [
            "web research and retrieval tools",
            "structured generation model",
            "CRM and document connectors",
        ],
        "document-intelligence": [
            "OCR and layout model",
            "structured extraction model",
            "business rules and human review queue",
        ],
    }
    return requirements[template.slug]


def create_proposal(
    session: Session,
    account_id: uuid.UUID,
    payload: SolutionProposalCreate,
) -> SolutionProposal:
    _ensure_editable(session, account_id)
    _require_discovery_approved(session, account_id)
    _ensure_solution_editable(session, account_id)
    ensure_catalog(session)
    template = get_template_or_raise(session, payload.solution_template_id)
    needs = _load_account_needs(session, account_id, payload.need_ids)
    if payload.deployment_option.value not in template.deployment_options:
        raise SolutionConflictError("The selected deployment is not supported by this template")

    matched_need_count = session.scalar(
        select(func.count(SolutionMatch.id)).where(
            SolutionMatch.account_id == account_id,
            SolutionMatch.solution_template_id == template.id,
            SolutionMatch.confirmed_need_id.in_(payload.need_ids),
        )
    )
    if matched_need_count != len(set(payload.need_ids)):
        raise SolutionPrerequisiteError("Generate solution matches before creating a proposal")
    duplicate = session.scalar(
        select(SolutionProposal.id).where(
            SolutionProposal.account_id == account_id,
            SolutionProposal.solution_template_id == template.id,
            SolutionProposal.status.in_(
                [SolutionProposalStatus.DRAFT, SolutionProposalStatus.NEEDS_REVISION]
            ),
        )
    )
    if duplicate is not None:
        raise SolutionConflictError("An editable proposal already exists for this template")

    _ensure_solution_started(session, account_id)
    account = accounts_service.get_account_or_raise(session, account_id)
    need_titles = ", ".join(need.title for need in needs)
    impact = (
        "; ".join(need.business_impact for need in needs if need.business_impact)
        or "Expected impact must be quantified during the POC."
    )
    constraints = [need.constraints for need in needs if need.constraints]
    proposal = SolutionProposal(
        account_id=account_id,
        solution_template_id=template.id,
        title=f"{template.name} for {account.name}",
        executive_summary=(
            f"Use the simulated {template.name} catalog pattern to address: {need_titles}. "
            "This is a draft solution proposal and requires human approval."
        ),
        why_fit=(
            f"The catalog pattern targets {', '.join(template.target_pain_points)}. "
            f"It is mapped only to confirmed need records: {need_titles}."
        ),
        architecture=template.architecture,
        required_data=template.required_data,
        model_tool_requirements=_model_tool_requirements(template),
        deployment_option=payload.deployment_option,
        security_considerations=[
            "Enforce least-privilege access and auditable human approval.",
            "Validate data residency, retention, and provider terms before production use.",
        ],
        risks=[*template.known_limitations, *constraints],
        expected_business_impact=impact,
        success_metrics=list(
            dict.fromkeys([*(need.success_metric for need in needs), *template.success_metrics])
        ),
        status=SolutionProposalStatus.DRAFT,
    )
    proposal.derived_needs.extend(needs)
    session.add(proposal)
    session.flush()
    accounts_service.add_activity(
        session,
        account_id=account_id,
        event_type="solution.proposal_created",
        entity_type="solution_proposal",
        entity_id=str(proposal.id),
        summary=f"Draft solution proposal created: {proposal.title}",
        metadata={
            "template_id": str(template.id),
            "derived_from_need_ids": [str(need.id) for need in needs],
        },
    )
    session.commit()
    return get_proposal_or_raise(session, proposal.id)


def update_proposal(
    session: Session,
    proposal_id: uuid.UUID,
    payload: SolutionProposalUpdate,
) -> SolutionProposal:
    proposal = get_proposal_or_raise(session, proposal_id)
    _ensure_editable(session, proposal.account_id)
    _ensure_solution_editable(session, proposal.account_id)
    if proposal.status not in {
        SolutionProposalStatus.DRAFT,
        SolutionProposalStatus.NEEDS_REVISION,
    }:
        raise SolutionConflictError("Only draft or revision proposals can be edited")
    if (
        payload.deployment_option is not None
        and payload.deployment_option.value not in proposal.solution_template.deployment_options
    ):
        raise SolutionConflictError("The selected deployment is not supported by this template")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(proposal, field, value)
    proposal.updated_at = utc_now()
    accounts_service.add_activity(
        session,
        account_id=proposal.account_id,
        event_type="solution.proposal_updated",
        entity_type="solution_proposal",
        entity_id=str(proposal.id),
        summary=f"Solution proposal updated: {proposal.title}",
    )
    session.commit()
    return get_proposal_or_raise(session, proposal.id)


def review_proposal(
    session: Session,
    proposal_id: uuid.UUID,
    payload: SolutionReviewRequest,
) -> SolutionProposal:
    proposal = get_proposal_or_raise(session, proposal_id)
    _ensure_editable(session, proposal.account_id)
    _ensure_solution_editable(session, proposal.account_id)
    if proposal.status not in {
        SolutionProposalStatus.DRAFT,
        SolutionProposalStatus.NEEDS_REVISION,
    }:
        raise SolutionConflictError("This proposal is not awaiting review")

    proposal.status = {
        SolutionReviewDecision.ACCEPT: SolutionProposalStatus.ACCEPTED,
        SolutionReviewDecision.REJECT: SolutionProposalStatus.REJECTED,
        SolutionReviewDecision.NEEDS_REVISION: SolutionProposalStatus.NEEDS_REVISION,
    }[payload.decision]
    proposal.review_notes = payload.notes
    proposal.reviewed_at = utc_now()
    proposal.updated_at = proposal.reviewed_at
    accounts_service.add_activity(
        session,
        account_id=proposal.account_id,
        event_type=f"solution.proposal_{proposal.status.value}",
        entity_type="solution_proposal",
        entity_id=str(proposal.id),
        summary=f"Solution proposal marked {proposal.status.value.replace('_', ' ')}",
        metadata={"notes": payload.notes},
    )
    session.commit()

    if payload.decision == SolutionReviewDecision.ACCEPT:
        accounts_service.transition_workflow(
            session,
            proposal.account_id,
            WorkflowTransitionRequest(
                stage=StageName.SOLUTION,
                status=StageStatus.COMPLETED,
                reason=payload.notes,
            ),
        )
    return get_proposal_or_raise(session, proposal.id)
