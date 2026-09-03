"""Create Phase 1 account workflow tables.

Revision ID: 20260901_0001
Revises:
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260901_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


stage_names = (
    "research",
    "opportunity",
    "discovery",
    "solution",
    "poc",
    "evaluation",
    "business_case",
    "deployment",
)
stage_statuses = ("not_started", "in_progress", "blocked", "completed")
actor_types = ("system", "user")


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("industry", sa.String(length=120), nullable=True),
        sa.Column("region", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("current_stage", sa.String(length=40), server_default="research", nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_accounts_name_not_blank"),
        sa.CheckConstraint(f"current_stage IN {stage_names}", name="ck_accounts_current_stage"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_accounts_name", "accounts", ["name"], unique=False)
    op.create_index("ix_accounts_industry", "accounts", ["industry"], unique=False)
    op.create_index("ix_accounts_region", "accounts", ["region"], unique=False)

    op.create_table(
        "account_stage_states",
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("stage", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), server_default="not_started", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(f"stage IN {stage_names}", name="ck_stage_states_stage"),
        sa.CheckConstraint(f"status IN {stage_statuses}", name="ck_stage_states_status"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("account_id", "stage"),
        sa.UniqueConstraint("account_id", "stage", name="uq_account_stage"),
    )

    op.create_table(
        "activity_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("actor_type", sa.String(length=40), server_default="user", nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=True),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(f"actor_type IN {actor_types}", name="ck_activity_actor_type"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_activity_events_account_id", "activity_events", ["account_id"])
    op.create_index("ix_activity_events_created_at", "activity_events", ["created_at"])
    op.create_index("ix_activity_events_event_type", "activity_events", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_activity_events_event_type", table_name="activity_events")
    op.drop_index("ix_activity_events_created_at", table_name="activity_events")
    op.drop_index("ix_activity_events_account_id", table_name="activity_events")
    op.drop_table("activity_events")
    op.drop_table("account_stage_states")
    op.drop_index("ix_accounts_region", table_name="accounts")
    op.drop_index("ix_accounts_industry", table_name="accounts")
    op.drop_index("ix_accounts_name", table_name="accounts")
    op.drop_table("accounts")
