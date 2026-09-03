"""Create account agent runs and approval state.

Revision ID: 20260903_0008
Revises: 20260902_0007
Create Date: 2026-09-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260903_0008"
down_revision: str | None = "20260902_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

run_statuses = ("completed", "awaiting_approval", "action_completed", "rejected", "failed")
providers = ("guided", "openai")
action_statuses = ("none", "pending", "executed", "rejected", "failed")


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("provider_response_id", sa.String(length=160), nullable=True),
        sa.Column("stage_snapshot", sa.String(length=80), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("observations", sa.JSON(), nullable=False),
        sa.Column("plan", sa.JSON(), nullable=False),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("trace", sa.JSON(), nullable=False),
        sa.Column("action_key", sa.String(length=100), nullable=True),
        sa.Column("action_title", sa.String(length=240), nullable=True),
        sa.Column("action_description", sa.Text(), nullable=True),
        sa.Column("action_reason", sa.Text(), nullable=True),
        sa.Column("action_target_path", sa.String(length=500), nullable=True),
        sa.Column(
            "action_requires_approval", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column("action_status", sa.String(length=40), nullable=False),
        sa.Column("action_result", sa.JSON(), nullable=False),
        sa.Column("approval_note", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(f"status IN {run_statuses}", name="ck_agent_runs_status"),
        sa.CheckConstraint(f"provider IN {providers}", name="ck_agent_runs_provider"),
        sa.CheckConstraint(
            f"action_status IN {action_statuses}", name="ck_agent_runs_action_status"
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_runs_account_created", "agent_runs", ["account_id", "created_at"])
    op.create_index("ix_agent_runs_account_status", "agent_runs", ["account_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_agent_runs_account_status", table_name="agent_runs")
    op.drop_index("ix_agent_runs_account_created", table_name="agent_runs")
    op.drop_table("agent_runs")
