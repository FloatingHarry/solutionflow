import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.db.session import SessionLocal
from app.modules.accounts import service as accounts_service
from app.modules.accounts.enums import StageName, StageStatus
from app.modules.accounts.models import Account
from app.modules.accounts.schemas import WorkflowTransitionRequest
from app.modules.research.enums import (
    ClaimReviewStatus,
    ResearchProviderName,
    ResearchStatus,
    ReviewDecision,
)
from app.modules.research.models import (
    CompanyProfile,
    Evidence,
    ProfileClaim,
    ResearchRun,
    Source,
)
from app.modules.research.providers.base import (
    ResearchInput,
    ResearchProviderConfigurationError,
)
from app.modules.research.providers.factory import get_research_provider
from app.modules.research.schemas import ResearchReviewRequest, ResearchRunCreate

ACTIVE_STATUSES = {ResearchStatus.QUEUED, ResearchStatus.RUNNING}


class ResearchRunNotFoundError(Exception):
    pass


class ResearchConflictError(Exception):
    pass


class ArchivedAccountError(Exception):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC)


def configured_provider() -> ResearchProviderName:
    try:
        return ResearchProviderName(settings.research_provider)
    except ValueError:
        return ResearchProviderName.MOCK


def get_run_or_raise(session: Session, run_id: uuid.UUID) -> ResearchRun:
    run = session.get(ResearchRun, run_id)
    if run is None:
        raise ResearchRunNotFoundError
    return run


def _set_research_stage_in_progress(session: Session, account_id: uuid.UUID) -> None:
    _account, stages = accounts_service.get_workflow(session, account_id)
    research_stage = next(state for state in stages if state.stage == StageName.RESEARCH)
    if research_stage.status in {StageStatus.NOT_STARTED, StageStatus.BLOCKED}:
        accounts_service.transition_workflow(
            session,
            account_id,
            WorkflowTransitionRequest(
                stage=StageName.RESEARCH,
                status=StageStatus.IN_PROGRESS,
                reason="Research run started",
            ),
        )


def _set_research_stage_blocked(session: Session, account_id: uuid.UUID, reason: str) -> None:
    _account, stages = accounts_service.get_workflow(session, account_id)
    research_stage = next(state for state in stages if state.stage == StageName.RESEARCH)
    if research_stage.status == StageStatus.IN_PROGRESS:
        accounts_service.transition_workflow(
            session,
            account_id,
            WorkflowTransitionRequest(
                stage=StageName.RESEARCH,
                status=StageStatus.BLOCKED,
                reason=reason[:500],
            ),
        )


def create_research_run(
    session: Session,
    account_id: uuid.UUID,
    payload: ResearchRunCreate,
    *,
    retry_of_id: uuid.UUID | None = None,
) -> ResearchRun:
    account = accounts_service.get_account_or_raise(session, account_id)
    if account.archived_at is not None:
        raise ArchivedAccountError

    active_run = session.scalar(
        select(ResearchRun).where(
            ResearchRun.account_id == account_id,
            ResearchRun.status.in_(ACTIVE_STATUSES),
        )
    )
    if active_run is not None:
        raise ResearchConflictError("A research run is already active for this account")

    provider_name = payload.provider or configured_provider()
    get_research_provider(provider_name)
    _set_research_stage_in_progress(session, account_id)

    run = ResearchRun(
        account_id=account_id,
        retry_of_id=retry_of_id,
        status=ResearchStatus.QUEUED,
        provider=provider_name,
        query_plan={
            "company": account.name,
            "website": account.website,
            "industry": account.industry,
            "region": account.region,
        },
    )
    session.add(run)
    session.flush()
    accounts_service.add_activity(
        session,
        account_id=account_id,
        event_type="research.queued",
        entity_type="research_run",
        entity_id=str(run.id),
        summary=f"Research queued using {provider_name.value}",
        metadata={"provider": provider_name.value, "retry_of_id": str(retry_of_id or "")},
    )
    session.commit()
    session.refresh(run)
    return run


def execute_research(session: Session, run_id: uuid.UUID) -> ResearchRun:
    run = get_run_or_raise(session, run_id)
    if run.status != ResearchStatus.QUEUED:
        return run

    run.status = ResearchStatus.RUNNING
    run.started_at = utc_now()
    run.updated_at = run.started_at
    accounts_service.add_activity(
        session,
        account_id=run.account_id,
        event_type="research.started",
        entity_type="research_run",
        entity_id=str(run.id),
        summary="Research started",
        metadata={"provider": run.provider.value},
    )
    session.commit()

    try:
        account = session.get(Account, run.account_id)
        if account is None:
            raise accounts_service.AccountNotFoundError

        provider = get_research_provider(run.provider)
        result = provider.research(
            ResearchInput(
                account_name=account.name,
                website=account.website,
                industry=account.industry,
                region=account.region,
                notes=account.notes,
            )
        )

        profile = CompanyProfile(
            account_id=account.id,
            research_run_id=run.id,
            summary=result.summary,
            is_simulated=result.is_simulated,
        )
        session.add(profile)
        session.flush()

        source_by_key: dict[str, Source] = {}
        for artifact in result.sources:
            hash_input = artifact.content_excerpt or artifact.url or artifact.title
            source = Source(
                account_id=account.id,
                research_run_id=run.id,
                source_type=artifact.source_type,
                title=artifact.title,
                url=artifact.url,
                publisher=artifact.publisher,
                content_excerpt=artifact.content_excerpt,
                content_hash=hashlib.sha256(hash_input.encode("utf-8")).hexdigest(),
                is_official=artifact.is_official,
                source_metadata=artifact.metadata,
            )
            session.add(source)
            source_by_key[artifact.key] = source
        session.flush()

        for position, artifact in enumerate(result.claims):
            claim = ProfileClaim(
                profile_id=profile.id,
                section=artifact.section,
                statement=artifact.statement,
                confidence=artifact.confidence,
                is_inference=artifact.is_inference,
                position=position,
            )
            session.add(claim)
            for evidence_artifact in artifact.evidence:
                source = source_by_key.get(evidence_artifact.source_key)
                if source is None:
                    continue
                evidence = Evidence(
                    account_id=account.id,
                    research_run_id=run.id,
                    source_id=source.id,
                    supporting_text=evidence_artifact.supporting_text,
                    locator=evidence_artifact.locator,
                    confidence=evidence_artifact.confidence,
                    verification_status=evidence_artifact.verification_status,
                )
                session.add(evidence)
                claim.evidence_items.append(evidence)

        run.status = ResearchStatus.NEEDS_REVIEW
        run.finished_at = utc_now()
        run.updated_at = run.finished_at
        run.provider_response_id = result.provider_response_id
        run.query_plan = {**run.query_plan, **result.query_plan}
        accounts_service.add_activity(
            session,
            account_id=run.account_id,
            event_type="research.ready_for_review",
            entity_type="research_run",
            entity_id=str(run.id),
            summary="Research completed and needs human review",
            metadata={
                "provider": run.provider.value,
                "simulated": result.is_simulated,
                "source_count": len(result.sources),
                "claim_count": len(result.claims),
            },
        )
        session.commit()
        session.refresh(run)
        return run
    except Exception as exc:
        session.rollback()
        failed_run = get_run_or_raise(session, run_id)
        failed_run.status = ResearchStatus.FAILED
        failed_run.error_message = str(exc)[:2000]
        failed_run.finished_at = utc_now()
        failed_run.updated_at = failed_run.finished_at
        accounts_service.add_activity(
            session,
            account_id=failed_run.account_id,
            event_type="research.failed",
            entity_type="research_run",
            entity_id=str(failed_run.id),
            summary="Research failed",
            metadata={"error": failed_run.error_message},
        )
        session.commit()
        _set_research_stage_blocked(session, failed_run.account_id, "Research run failed")
        return failed_run


def run_research_task(run_id: uuid.UUID) -> None:
    with SessionLocal() as session:
        execute_research(session, run_id)


def retry_research_run(session: Session, run_id: uuid.UUID) -> ResearchRun:
    previous = get_run_or_raise(session, run_id)
    if previous.status not in {ResearchStatus.FAILED, ResearchStatus.REJECTED}:
        raise ResearchConflictError("Only failed or rejected research can be retried")
    return create_research_run(
        session,
        previous.account_id,
        ResearchRunCreate(provider=previous.provider),
        retry_of_id=previous.id,
    )


def review_research_run(
    session: Session, run_id: uuid.UUID, payload: ResearchReviewRequest
) -> ResearchRun:
    run = get_run_or_raise(session, run_id)
    if run.status != ResearchStatus.NEEDS_REVIEW or run.profile is None:
        raise ResearchConflictError("This research run is not awaiting review")

    now = utc_now()
    run.review_notes = payload.notes
    run.reviewed_at = now
    run.updated_at = now
    if payload.decision == ReviewDecision.APPROVE:
        run.status = ResearchStatus.COMPLETED
        run.profile.reviewed_at = now
        for claim in run.profile.claims:
            claim.review_status = ClaimReviewStatus.HUMAN_REVIEWED
        event_type = "research.approved"
        summary = "Research approved"
    else:
        run.status = ResearchStatus.REJECTED
        for claim in run.profile.claims:
            claim.review_status = ClaimReviewStatus.HUMAN_REJECTED
        event_type = "research.rejected"
        summary = "Research rejected"

    accounts_service.add_activity(
        session,
        account_id=run.account_id,
        event_type=event_type,
        entity_type="research_run",
        entity_id=str(run.id),
        summary=summary,
        metadata={"notes": payload.notes},
    )
    session.commit()

    if payload.decision == ReviewDecision.APPROVE:
        _account, stages = accounts_service.get_workflow(session, run.account_id)
        research_stage = next(state for state in stages if state.stage == StageName.RESEARCH)
        if research_stage.status in {StageStatus.IN_PROGRESS, StageStatus.BLOCKED}:
            accounts_service.transition_workflow(
                session,
                run.account_id,
                WorkflowTransitionRequest(
                    stage=StageName.RESEARCH,
                    status=StageStatus.COMPLETED,
                    reason=payload.notes,
                ),
            )
    else:
        _set_research_stage_blocked(session, run.account_id, payload.notes)

    return get_run_or_raise(session, run_id)


def get_research_workspace(
    session: Session, account_id: uuid.UUID
) -> tuple[list[ResearchRun], ResearchRun | None]:
    accounts_service.get_account_or_raise(session, account_id)
    runs = list(
        session.scalars(
            select(ResearchRun)
            .where(ResearchRun.account_id == account_id)
            .options(
                selectinload(ResearchRun.sources),
                selectinload(ResearchRun.profile)
                .selectinload(CompanyProfile.claims)
                .selectinload(ProfileClaim.evidence_items)
                .selectinload(Evidence.source),
            )
            .order_by(ResearchRun.created_at.desc())
            .limit(20)
        ).all()
    )
    return runs, runs[0] if runs else None


def get_research_run_detail(session: Session, run_id: uuid.UUID) -> ResearchRun:
    run = session.scalar(
        select(ResearchRun)
        .where(ResearchRun.id == run_id)
        .options(
            selectinload(ResearchRun.sources),
            selectinload(ResearchRun.profile)
            .selectinload(CompanyProfile.claims)
            .selectinload(ProfileClaim.evidence_items)
            .selectinload(Evidence.source),
        )
    )
    if run is None:
        raise ResearchRunNotFoundError
    return run


__all__ = [
    "ArchivedAccountError",
    "ResearchConflictError",
    "ResearchProviderConfigurationError",
    "ResearchRunNotFoundError",
]
