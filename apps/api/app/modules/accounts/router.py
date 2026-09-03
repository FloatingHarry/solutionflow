import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.db.session import SessionDep
from app.modules.accounts import service
from app.modules.accounts.models import ActivityEvent
from app.modules.accounts.schemas import (
    AccountCreate,
    AccountListResponse,
    AccountResponse,
    AccountUpdate,
    ActivityListResponse,
    ActivityResponse,
    WorkflowResponse,
    WorkflowTransitionRequest,
)

router = APIRouter(prefix="/accounts", tags=["accounts"])


def not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")


def activity_response(activity: ActivityEvent) -> ActivityResponse:
    return ActivityResponse(
        id=activity.id,
        account_id=activity.account_id,
        actor_type=activity.actor_type,
        event_type=activity.event_type,
        entity_type=activity.entity_type,
        entity_id=activity.entity_id,
        summary=activity.summary,
        metadata=activity.details,
        created_at=activity.created_at,
    )


@router.get("", response_model=AccountListResponse)
def get_accounts(
    session: SessionDep,
    q: str | None = Query(default=None, max_length=200),
    include_archived: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AccountListResponse:
    items, total = service.list_accounts(
        session,
        query=q,
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )
    return AccountListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def post_account(payload: AccountCreate, session: SessionDep) -> AccountResponse:
    return AccountResponse.model_validate(service.create_account(session, payload))


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(account_id: uuid.UUID, session: SessionDep) -> AccountResponse:
    try:
        return AccountResponse.model_validate(service.get_account_or_raise(session, account_id))
    except service.AccountNotFoundError as exc:
        raise not_found() from exc


@router.patch("/{account_id}", response_model=AccountResponse)
def patch_account(
    account_id: uuid.UUID,
    payload: AccountUpdate,
    session: SessionDep,
) -> AccountResponse:
    try:
        return AccountResponse.model_validate(service.update_account(session, account_id, payload))
    except service.AccountNotFoundError as exc:
        raise not_found() from exc


@router.post("/{account_id}/archive", response_model=AccountResponse)
def post_archive(account_id: uuid.UUID, session: SessionDep) -> AccountResponse:
    try:
        return AccountResponse.model_validate(service.archive_account(session, account_id))
    except service.AccountNotFoundError as exc:
        raise not_found() from exc


@router.post("/{account_id}/restore", response_model=AccountResponse)
def post_restore(account_id: uuid.UUID, session: SessionDep) -> AccountResponse:
    try:
        return AccountResponse.model_validate(service.restore_account(session, account_id))
    except service.AccountNotFoundError as exc:
        raise not_found() from exc


@router.get("/{account_id}/workflow", response_model=WorkflowResponse)
def get_account_workflow(account_id: uuid.UUID, session: SessionDep) -> WorkflowResponse:
    try:
        account, stages = service.get_workflow(session, account_id)
        return WorkflowResponse(
            account_id=account.id,
            current_stage=account.current_stage,
            stages=stages,
        )
    except service.AccountNotFoundError as exc:
        raise not_found() from exc


@router.post("/{account_id}/workflow/transitions", response_model=WorkflowResponse)
def post_workflow_transition(
    account_id: uuid.UUID,
    payload: WorkflowTransitionRequest,
    session: SessionDep,
) -> WorkflowResponse:
    try:
        account, stages = service.transition_workflow(session, account_id, payload)
        return WorkflowResponse(
            account_id=account.id,
            current_stage=account.current_stage,
            stages=stages,
        )
    except service.AccountNotFoundError as exc:
        raise not_found() from exc
    except service.InvalidWorkflowTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/{account_id}/activities", response_model=ActivityListResponse)
def get_account_activities(account_id: uuid.UUID, session: SessionDep) -> ActivityListResponse:
    try:
        activities = service.list_activities(session, account_id)
        return ActivityListResponse(
            items=[activity_response(activity) for activity in activities],
            total=len(activities),
        )
    except service.AccountNotFoundError as exc:
        raise not_found() from exc
