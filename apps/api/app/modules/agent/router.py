import uuid

from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.db.session import SessionDep
from app.modules.accounts import service as accounts_service
from app.modules.agent import service
from app.modules.agent.models import AgentRun
from app.modules.agent.schemas import (
    AgentActionDecision,
    AgentActionResponse,
    AgentRunCreate,
    AgentRunResponse,
    AgentWorkspaceResponse,
)

router = APIRouter(tags=["account-agent"])


def serialize_run(run: AgentRun) -> AgentRunResponse:
    action = None
    if run.action_key and run.action_title and run.action_description and run.action_reason:
        action = AgentActionResponse(
            key=run.action_key,
            title=run.action_title,
            description=run.action_description,
            reason=run.action_reason,
            target_path=run.action_target_path,
            requires_approval=run.action_requires_approval,
            status=run.action_status,
            result=run.action_result,
        )
    return AgentRunResponse(
        id=run.id,
        account_id=run.account_id,
        goal=run.goal,
        status=run.status,
        provider=run.provider,
        model=run.model,
        provider_response_id=run.provider_response_id,
        stage_snapshot=run.stage_snapshot,
        summary=run.summary,
        observations=run.observations,
        plan=run.plan,
        question=run.question,
        trace=run.trace,
        action=action,
        approval_note=run.approval_note,
        error_message=run.error_message,
        created_at=run.created_at,
        updated_at=run.updated_at,
        completed_at=run.completed_at,
    )


def account_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")


def run_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")


def handle_agent_error(exc: Exception) -> HTTPException:
    if isinstance(exc, service.ArchivedAccountError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Archived account is read-only"
        )
    if isinstance(exc, service.AgentConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, service.AgentActionError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/accounts/{account_id}/agent",
    response_model=AgentWorkspaceResponse,
)
def get_agent_workspace(account_id: uuid.UUID, session: SessionDep) -> AgentWorkspaceResponse:
    try:
        runs = service.list_runs(session, account_id)
    except accounts_service.AccountNotFoundError as exc:
        raise account_not_found() from exc
    mode = service.configured_provider()
    return AgentWorkspaceResponse(
        account_id=account_id,
        live_agent_available=bool(settings.openai_api_key),
        mode=mode,
        model=settings.openai_agent_model if mode.value == "openai" else None,
        capabilities=service.CAPABILITIES,
        starter_prompts=service.STARTER_PROMPTS,
        runs=[serialize_run(run) for run in runs],
    )


@router.post(
    "/accounts/{account_id}/agent/runs",
    response_model=AgentRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_agent_run(
    account_id: uuid.UUID, payload: AgentRunCreate, session: SessionDep
) -> AgentRunResponse:
    try:
        return serialize_run(service.create_run(session, account_id, payload.goal))
    except accounts_service.AccountNotFoundError as exc:
        raise account_not_found() from exc
    except Exception as exc:
        raise handle_agent_error(exc) from exc


@router.post("/agent-runs/{run_id}/approve", response_model=AgentRunResponse)
def approve_agent_action(
    run_id: uuid.UUID, payload: AgentActionDecision, session: SessionDep
) -> AgentRunResponse:
    try:
        return serialize_run(service.approve_action(session, run_id, payload.note))
    except service.AgentRunNotFoundError as exc:
        raise run_not_found() from exc
    except Exception as exc:
        raise handle_agent_error(exc) from exc


@router.post("/agent-runs/{run_id}/reject", response_model=AgentRunResponse)
def reject_agent_action(
    run_id: uuid.UUID, payload: AgentActionDecision, session: SessionDep
) -> AgentRunResponse:
    try:
        return serialize_run(service.reject_action(session, run_id, payload.note))
    except service.AgentRunNotFoundError as exc:
        raise run_not_found() from exc
    except Exception as exc:
        raise handle_agent_error(exc) from exc
