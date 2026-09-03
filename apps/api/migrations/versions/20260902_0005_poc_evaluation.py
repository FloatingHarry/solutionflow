"""Create Phase 5 POC plans, evaluation metrics, and decisions.

Revision ID: 20260902_0005
Revises: 20260902_0004
Create Date: 2026-09-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260902_0005"
down_revision: str | None = "20260902_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


plan_statuses = ("draft", "needs_revision", "approved", "rejected")
metric_operators = ("gte", "lte")
metric_statuses = ("pending", "pass", "fail")
decision_types = ("proceed", "iterate", "reject")


def upgrade() -> None:
    op.create_table(
        "poc_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("solution_proposal_id", sa.Uuid(), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("business_problem", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("required_data", sa.JSON(), nullable=False),
        sa.Column("architecture", sa.Text(), nullable=False),
        sa.Column("timeline_days", sa.Integer(), server_default="14", nullable=False),
        sa.Column("evaluation_dataset", sa.Text(), nullable=False),
        sa.Column("expected_output", sa.Text(), nullable=False),
        sa.Column("risks", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=40), server_default="draft", nullable=False),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("timeline_days > 0", name="ck_poc_plans_timeline_positive"),
        sa.CheckConstraint(f"status IN {plan_statuses}", name="ck_poc_plans_status"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["solution_proposal_id"], ["solution_proposals.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("solution_proposal_id", name="uq_poc_plans_solution_proposal"),
    )
    op.create_index("ix_poc_plans_account_status", "poc_plans", ["account_id", "status"])

    op.create_table(
        "poc_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("poc_plan_id", sa.Uuid(), nullable=False),
        sa.Column("metric_key", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("target_operator", sa.String(length=20), nullable=False),
        sa.Column("target_value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=40), nullable=False),
        sa.Column("actual_value", sa.Float(), nullable=True),
        sa.Column("result_status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("position >= 0", name="ck_poc_metrics_position_nonnegative"),
        sa.CheckConstraint(
            f"target_operator IN {metric_operators}", name="ck_poc_metrics_operator"
        ),
        sa.CheckConstraint(
            f"result_status IN {metric_statuses}", name="ck_poc_metrics_result_status"
        ),
        sa.ForeignKeyConstraint(["poc_plan_id"], ["poc_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("poc_plan_id", "metric_key", name="uq_poc_metrics_plan_key"),
    )

    op.create_table(
        "poc_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("poc_plan_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(f"decision IN {decision_types}", name="ck_poc_decisions_decision"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["poc_plan_id"], ["poc_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_poc_decisions_plan_created", "poc_decisions", ["poc_plan_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_poc_decisions_plan_created", table_name="poc_decisions")
    op.drop_table("poc_decisions")
    op.drop_table("poc_metrics")
    op.drop_index("ix_poc_plans_account_status", table_name="poc_plans")
    op.drop_table("poc_plans")
