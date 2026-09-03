import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.core.config import settings
from app.db.session import SessionDep
from app.modules.accounts import service as accounts_service
from app.modules.research import service
from app.modules.research.models import CompanyProfile, ResearchRun, Source
from app.modules.research.schemas import (
    CitationResponse,
    CompanyProfileResponse,
    ProfileClaimResponse,
    ResearchReviewRequest,
    ResearchRunCreate,
    ResearchRunResponse,
    ResearchWorkspaceResponse,
    SourceResponse,
)

router = APIRouter(tags=["research"])


def serialize_source(source: Source) -> SourceResponse:
    return SourceResponse(
        id=source.id,
        source_type=source.source_type,
        title=source.title,
        url=source.url,
        publisher=source.publisher,
        published_at=source.published_at,
        retrieved_at=source.retrieved_at,
        content_excerpt=source.content_excerpt,
        is_official=source.is_official,
        metadata=source.source_metadata,
    )


def serialize_profile(profile: CompanyProfile | None) -> CompanyProfileResponse | None:
    if profile is None:
        return None
    claims = []
    for claim in profile.claims:
        citations = [
            CitationResponse(
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
            for evidence in claim.evidence_items
        ]
        claims.append(
            ProfileClaimResponse(
                id=claim.id,
                section=claim.section,
                statement=claim.statement,
                confidence=claim.confidence,
                is_inference=claim.is_inference,
                review_status=claim.review_status,
                citations=citations,
            )
        )
    return CompanyProfileResponse(
        id=profile.id,
        research_run_id=profile.research_run_id,
        summary=profile.summary,
        is_simulated=profile.is_simulated,
        reviewed_at=profile.reviewed_at,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        claims=claims,
    )


def serialize_workspace(
    account_id: uuid.UUID, runs: list[ResearchRun], latest: ResearchRun | None
) -> ResearchWorkspaceResponse:
    return ResearchWorkspaceResponse(
        account_id=account_id,
        configured_provider=service.configured_provider(),
        live_research_available=bool(settings.openai_api_key),
        latest_run=ResearchRunResponse.model_validate(latest) if latest else None,
        run_history=[ResearchRunResponse.model_validate(run) for run in runs],
        profile=serialize_profile(latest.profile if latest else None),
        sources=[serialize_source(source) for source in (latest.sources if latest else [])],
    )


def account_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")


def research_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research run not found")


def handle_research_error(exc: Exception) -> HTTPException:
    if isinstance(exc, service.ResearchConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, service.ArchivedAccountError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Archived account is read-only",
        )
    if isinstance(exc, service.ResearchProviderConfigurationError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/accounts/{account_id}/research", response_model=ResearchWorkspaceResponse)
def get_account_research(account_id: uuid.UUID, session: SessionDep) -> ResearchWorkspaceResponse:
    try:
        runs, latest = service.get_research_workspace(session, account_id)
        return serialize_workspace(account_id, runs, latest)
    except accounts_service.AccountNotFoundError as exc:
        raise account_not_found() from exc


@router.post(
    "/accounts/{account_id}/research-runs",
    response_model=ResearchRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_research(
    account_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    payload: ResearchRunCreate | None = None,
) -> ResearchRunResponse:
    try:
        run = service.create_research_run(session, account_id, payload or ResearchRunCreate())
        if settings.research_run_inline:
            run = service.execute_research(session, run.id)
        else:
            background_tasks.add_task(service.run_research_task, run.id)
        return ResearchRunResponse.model_validate(run)
    except accounts_service.AccountNotFoundError as exc:
        raise account_not_found() from exc
    except Exception as exc:
        raise handle_research_error(exc) from exc


@router.get("/research-runs/{run_id}", response_model=ResearchRunResponse)
def get_research_run(run_id: uuid.UUID, session: SessionDep) -> ResearchRunResponse:
    try:
        return ResearchRunResponse.model_validate(service.get_research_run_detail(session, run_id))
    except service.ResearchRunNotFoundError as exc:
        raise research_not_found() from exc


@router.post(
    "/research-runs/{run_id}/retry",
    response_model=ResearchRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_research(
    run_id: uuid.UUID, background_tasks: BackgroundTasks, session: SessionDep
) -> ResearchRunResponse:
    try:
        run = service.retry_research_run(session, run_id)
        if settings.research_run_inline:
            run = service.execute_research(session, run.id)
        else:
            background_tasks.add_task(service.run_research_task, run.id)
        return ResearchRunResponse.model_validate(run)
    except service.ResearchRunNotFoundError as exc:
        raise research_not_found() from exc
    except Exception as exc:
        raise handle_research_error(exc) from exc


@router.post("/research-runs/{run_id}/review", response_model=ResearchRunResponse)
def review_research(
    run_id: uuid.UUID, payload: ResearchReviewRequest, session: SessionDep
) -> ResearchRunResponse:
    try:
        return ResearchRunResponse.model_validate(
            service.review_research_run(session, run_id, payload)
        )
    except service.ResearchRunNotFoundError as exc:
        raise research_not_found() from exc
    except Exception as exc:
        raise handle_research_error(exc) from exc
