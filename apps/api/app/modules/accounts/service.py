import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.accounts.enums import STAGE_ORDER, ActorType, StageName, StageStatus
from app.modules.accounts.models import Account, AccountStageState, ActivityEvent
from app.modules.accounts.schemas import AccountCreate, AccountUpdate, WorkflowTransitionRequest


class AccountNotFoundError(Exception):
    pass


class InvalidWorkflowTransitionError(Exception):
    pass


ALLOWED_TRANSITIONS: dict[StageStatus, set[StageStatus]] = {
    StageStatus.NOT_STARTED: {StageStatus.IN_PROGRESS},
    StageStatus.IN_PROGRESS: {StageStatus.BLOCKED, StageStatus.COMPLETED},
    StageStatus.BLOCKED: {StageStatus.IN_PROGRESS, StageStatus.COMPLETED},
    StageStatus.COMPLETED: set(),
}


def utc_now() -> datetime:
    return datetime.now(UTC)


def get_account_or_raise(session: Session, account_id: uuid.UUID) -> Account:
    account = session.get(Account, account_id)
    if account is None:
        raise AccountNotFoundError
    return account


def add_activity(
    session: Session,
    *,
    account_id: uuid.UUID,
    event_type: str,
    summary: str,
    entity_type: str = "account",
    entity_id: str | None = None,
    actor_type: ActorType = ActorType.USER,
    metadata: dict | None = None,
) -> ActivityEvent:
    activity = ActivityEvent(
        account_id=account_id,
        actor_type=actor_type,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id or str(account_id),
        summary=summary,
        details=metadata or {},
    )
    session.add(activity)
    return activity


def create_account(session: Session, payload: AccountCreate) -> Account:
    account = Account(**payload.model_dump())
    session.add(account)
    session.flush()

    for stage in STAGE_ORDER:
        session.add(AccountStageState(account_id=account.id, stage=stage))

    add_activity(
        session,
        account_id=account.id,
        event_type="account.created",
        summary=f"Account created: {account.name}",
        actor_type=ActorType.USER,
    )
    session.commit()
    session.refresh(account)
    return account


def list_accounts(
    session: Session,
    *,
    query: str | None,
    include_archived: bool,
    limit: int,
    offset: int,
) -> tuple[list[Account], int]:
    filters = []
    if not include_archived:
        filters.append(Account.archived_at.is_(None))
    if query:
        pattern = f"%{query.strip().lower()}%"
        filters.append(
            or_(
                func.lower(Account.name).like(pattern),
                func.lower(func.coalesce(Account.industry, "")).like(pattern),
                func.lower(func.coalesce(Account.region, "")).like(pattern),
            )
        )

    statement = select(Account).where(*filters)
    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    items = list(
        session.scalars(
            statement.order_by(Account.updated_at.desc()).limit(limit).offset(offset)
        ).all()
    )
    return items, total


def update_account(session: Session, account_id: uuid.UUID, payload: AccountUpdate) -> Account:
    account = get_account_or_raise(session, account_id)
    changes = payload.model_dump(exclude_unset=True)
    changed_fields = []
    for field, value in changes.items():
        if getattr(account, field) != value:
            setattr(account, field, value)
            changed_fields.append(field)

    if changed_fields:
        account.version += 1
        account.updated_at = utc_now()
        add_activity(
            session,
            account_id=account.id,
            event_type="account.updated",
            summary="Account details updated",
            metadata={"fields": changed_fields},
        )
        session.commit()
        session.refresh(account)
    return account


def archive_account(session: Session, account_id: uuid.UUID) -> Account:
    account = get_account_or_raise(session, account_id)
    if account.archived_at is None:
        account.archived_at = utc_now()
        account.version += 1
        add_activity(
            session,
            account_id=account.id,
            event_type="account.archived",
            summary="Account archived",
        )
        session.commit()
        session.refresh(account)
    return account


def restore_account(session: Session, account_id: uuid.UUID) -> Account:
    account = get_account_or_raise(session, account_id)
    if account.archived_at is not None:
        account.archived_at = None
        account.version += 1
        add_activity(
            session,
            account_id=account.id,
            event_type="account.restored",
            summary="Account restored",
        )
        session.commit()
        session.refresh(account)
    return account


def get_workflow(
    session: Session, account_id: uuid.UUID
) -> tuple[Account, list[AccountStageState]]:
    account = get_account_or_raise(session, account_id)
    states = list(
        session.scalars(
            select(AccountStageState).where(AccountStageState.account_id == account_id)
        ).all()
    )
    states.sort(key=lambda state: STAGE_ORDER.index(state.stage))
    return account, states


def transition_workflow(
    session: Session,
    account_id: uuid.UUID,
    payload: WorkflowTransitionRequest,
) -> tuple[Account, list[AccountStageState]]:
    account, states = get_workflow(session, account_id)
    state_by_stage = {state.stage: state for state in states}
    state = state_by_stage[payload.stage]

    if payload.status not in ALLOWED_TRANSITIONS[state.status]:
        raise InvalidWorkflowTransitionError(
            f"Cannot move {payload.stage.value} from {state.status.value} to {payload.status.value}"
        )

    stage_index = STAGE_ORDER.index(payload.stage)
    if payload.status in {StageStatus.IN_PROGRESS, StageStatus.COMPLETED}:
        incomplete_previous = [
            previous.value
            for previous in STAGE_ORDER[:stage_index]
            if state_by_stage[previous].status != StageStatus.COMPLETED
        ]
        if incomplete_previous:
            raise InvalidWorkflowTransitionError(
                "Complete previous stages first: " + ", ".join(incomplete_previous)
            )

    now = utc_now()
    previous_status = state.status
    state.status = payload.status
    state.updated_at = now
    if payload.status == StageStatus.IN_PROGRESS and state.started_at is None:
        state.started_at = now
    if payload.status == StageStatus.COMPLETED:
        state.started_at = state.started_at or now
        state.completed_at = now

    first_incomplete = next(
        (
            candidate
            for candidate in STAGE_ORDER
            if state_by_stage[candidate].status != StageStatus.COMPLETED
        ),
        StageName.DEPLOYMENT,
    )
    account.current_stage = first_incomplete
    account.version += 1
    account.updated_at = now

    add_activity(
        session,
        account_id=account.id,
        event_type="workflow.transitioned",
        entity_type="workflow_stage",
        entity_id=payload.stage.value,
        summary=(
            f"{payload.stage.value.replace('_', ' ').title()} marked "
            f"{payload.status.value.replace('_', ' ')}"
        ),
        metadata={
            "stage": payload.stage.value,
            "from": previous_status.value,
            "to": payload.status.value,
            "reason": payload.reason,
        },
    )
    session.commit()
    session.refresh(account)
    return get_workflow(session, account_id)


def list_activities(session: Session, account_id: uuid.UUID) -> list[ActivityEvent]:
    get_account_or_raise(session, account_id)
    return list(
        session.scalars(
            select(ActivityEvent)
            .where(ActivityEvent.account_id == account_id)
            .order_by(ActivityEvent.created_at.desc())
        ).all()
    )
