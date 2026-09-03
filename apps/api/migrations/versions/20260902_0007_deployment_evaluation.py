"""Create Phase 7 deployment planning and system evaluation.

Revision ID: 20260902_0007
Revises: 20260902_0006
Create Date: 2026-09-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260902_0007"
down_revision: str | None = "20260902_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

deployment_options = ("saas_api", "eu_cloud", "private_on_premise")
deployment_statuses = ("in_progress", "blocked", "completed")
checklist_statuses = ("pending", "blocked", "completed")


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column("is_demo", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_index("ix_accounts_is_demo", "accounts", ["is_demo"])

    op.create_table(
        "deployment_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("business_case_id", sa.Uuid(), nullable=False),
        sa.Column("environment", sa.String(length=40), nullable=False),
        sa.Column("owner", sa.String(length=200), nullable=False),
        sa.Column("target_launch_date", sa.Date(), nullable=True),
        sa.Column("rollout_strategy", sa.Text(), nullable=False),
        sa.Column("integration_plan", sa.Text(), nullable=False),
        sa.Column("data_governance_plan", sa.Text(), nullable=False),
        sa.Column("monitoring_plan", sa.Text(), nullable=False),
        sa.Column("rollback_plan", sa.Text(), nullable=False),
        sa.Column("support_model", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), server_default="in_progress", nullable=False),
        sa.Column("readiness_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("completion_notes", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "readiness_score >= 0 AND readiness_score <= 100",
            name="ck_deployment_plans_readiness_range",
        ),
        sa.CheckConstraint(
            f"environment IN {deployment_options}", name="ck_deployment_plans_environment"
        ),
        sa.CheckConstraint(
            f"status IN {deployment_statuses}", name="ck_deployment_plans_status"
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["business_case_id"], ["business_cases.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", name="uq_deployment_plans_account"),
        sa.UniqueConstraint("business_case_id", name="uq_deployment_plans_business_case"),
    )
    op.create_index(
        "ix_deployment_plans_status", "deployment_plans", ["status", "updated_at"]
    )

    op.create_table(
        "deployment_checklist_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("deployment_plan_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("owner", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=40), server_default="pending", nullable=False),
        sa.Column("evidence_notes", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("position >= 0", name="ck_deployment_checklist_position"),
        sa.CheckConstraint(
            f"status IN {checklist_statuses}", name="ck_deployment_checklist_status"
        ),
        sa.ForeignKeyConstraint(
            ["deployment_plan_id"], ["deployment_plans.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "deployment_plan_id", "category", name="uq_deployment_checklist_plan_category"
        ),
    )

    op.create_table(
        "system_evaluation_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("methodology", sa.Text(), nullable=False),
        sa.Column("dataset_version", sa.String(length=80), nullable=False),
        sa.Column("is_deterministic", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("demo_account_count", sa.Integer(), nullable=False),
        sa.Column("total_tasks", sa.Integer(), nullable=False),
        sa.Column("passed_tasks", sa.Integer(), nullable=False),
        sa.Column("pass_rate", sa.Float(), nullable=False),
        sa.Column("hallucination_rate", sa.Float(), nullable=False),
        sa.Column("citation_correctness", sa.Float(), nullable=False),
        sa.Column("task_completion_rate", sa.Float(), nullable=False),
        sa.Column("mean_latency_ms", sa.Float(), nullable=False),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "completed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("total_tasks >= 0", name="ck_system_evaluation_total_tasks"),
        sa.CheckConstraint("passed_tasks >= 0", name="ck_system_evaluation_passed_tasks"),
        sa.CheckConstraint(
            "pass_rate >= 0 AND pass_rate <= 100", name="ck_system_evaluation_pass_rate"
        ),
        sa.CheckConstraint(
            "hallucination_rate >= 0 AND hallucination_rate <= 100",
            name="ck_system_evaluation_hallucination_rate",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_system_evaluation_runs_created", "system_evaluation_runs", ["created_at"]
    )

    op.create_table(
        "system_evaluation_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evaluation_run_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("label", sa.String(length=240), nullable=False),
        sa.Column("expected", sa.Text(), nullable=False),
        sa.Column("actual", sa.Text(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "score >= 0 AND score <= 100", name="ck_system_evaluation_task_score"
        ),
        sa.CheckConstraint("position >= 0", name="ck_system_evaluation_task_position"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["evaluation_run_id"], ["system_evaluation_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_system_evaluation_tasks_run_category",
        "system_evaluation_tasks",
        ["evaluation_run_id", "category"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_system_evaluation_tasks_run_category", table_name="system_evaluation_tasks"
    )
    op.drop_table("system_evaluation_tasks")
    op.drop_index("ix_system_evaluation_runs_created", table_name="system_evaluation_runs")
    op.drop_table("system_evaluation_runs")
    op.drop_table("deployment_checklist_items")
    op.drop_index("ix_deployment_plans_status", table_name="deployment_plans")
    op.drop_table("deployment_plans")
    op.drop_index("ix_accounts_is_demo", table_name="accounts")
    op.drop_column("accounts", "is_demo")
