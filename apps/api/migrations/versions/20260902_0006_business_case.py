"""Create Phase 6 business cases, deployment assessments, and account briefs.

Revision ID: 20260902_0006
Revises: 20260902_0005
Create Date: 2026-09-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260902_0006"
down_revision: str | None = "20260902_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


case_statuses = ("draft", "needs_revision", "approved", "rejected")
deployment_options = ("saas_api", "eu_cloud", "private_on_premise")
ratings = ("low", "medium", "high")


def upgrade() -> None:
    op.create_table(
        "business_cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("poc_plan_id", sa.Uuid(), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="EUR", nullable=False),
        sa.Column("number_employees", sa.Integer(), nullable=False),
        sa.Column("average_hourly_cost", sa.Float(), nullable=False),
        sa.Column("current_time_per_task_minutes", sa.Float(), nullable=False),
        sa.Column("tasks_per_employee_per_month", sa.Float(), nullable=False),
        sa.Column("expected_time_reduction_percent", sa.Float(), nullable=False),
        sa.Column("monthly_ai_cost", sa.Float(), nullable=False),
        sa.Column("implementation_cost", sa.Float(), nullable=False),
        sa.Column("current_monthly_cost", sa.Float(), nullable=False),
        sa.Column("estimated_new_labor_cost", sa.Float(), nullable=False),
        sa.Column("estimated_new_total_cost", sa.Float(), nullable=False),
        sa.Column("monthly_savings", sa.Float(), nullable=False),
        sa.Column("annual_savings", sa.Float(), nullable=False),
        sa.Column("estimated_first_year_roi_percent", sa.Float(), nullable=True),
        sa.Column("payback_period_months", sa.Float(), nullable=True),
        sa.Column("recommended_deployment", sa.String(length=40), nullable=False),
        sa.Column("deployment_rationale", sa.Text(), nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=40), server_default="draft", nullable=False),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("number_employees > 0", name="ck_business_cases_employees_positive"),
        sa.CheckConstraint("average_hourly_cost >= 0", name="ck_business_cases_hourly_cost"),
        sa.CheckConstraint(
            "current_time_per_task_minutes > 0", name="ck_business_cases_task_time_positive"
        ),
        sa.CheckConstraint(
            "tasks_per_employee_per_month > 0", name="ck_business_cases_tasks_positive"
        ),
        sa.CheckConstraint(
            "expected_time_reduction_percent >= 0 AND "
            "expected_time_reduction_percent <= 100",
            name="ck_business_cases_reduction_range",
        ),
        sa.CheckConstraint("monthly_ai_cost >= 0", name="ck_business_cases_ai_cost"),
        sa.CheckConstraint(
            "implementation_cost >= 0", name="ck_business_cases_implementation"
        ),
        sa.CheckConstraint(f"status IN {case_statuses}", name="ck_business_cases_status"),
        sa.CheckConstraint(
            f"recommended_deployment IN {deployment_options}",
            name="ck_business_cases_deployment",
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["poc_plan_id"], ["poc_plans.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("poc_plan_id", name="uq_business_cases_poc_plan"),
    )
    op.create_index(
        "ix_business_cases_account_status", "business_cases", ["account_id", "status"]
    )

    op.create_table(
        "deployment_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("business_case_id", sa.Uuid(), nullable=False),
        sa.Column("option", sa.String(length=40), nullable=False),
        sa.Column("cost", sa.String(length=20), nullable=False),
        sa.Column("implementation_difficulty", sa.String(length=20), nullable=False),
        sa.Column("data_privacy", sa.String(length=20), nullable=False),
        sa.Column("scalability", sa.String(length=20), nullable=False),
        sa.Column("maintenance", sa.String(length=20), nullable=False),
        sa.Column("latency", sa.String(length=20), nullable=False),
        sa.Column("compliance", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.JSON(), nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("position >= 0", name="ck_deployment_assessments_position"),
        sa.CheckConstraint(f"option IN {deployment_options}", name="ck_deployment_option"),
        sa.CheckConstraint(f"cost IN {ratings}", name="ck_deployment_cost"),
        sa.CheckConstraint(
            f"implementation_difficulty IN {ratings}", name="ck_deployment_difficulty"
        ),
        sa.CheckConstraint(f"data_privacy IN {ratings}", name="ck_deployment_privacy"),
        sa.CheckConstraint(f"scalability IN {ratings}", name="ck_deployment_scalability"),
        sa.CheckConstraint(f"maintenance IN {ratings}", name="ck_deployment_maintenance"),
        sa.CheckConstraint(f"latency IN {ratings}", name="ck_deployment_latency"),
        sa.CheckConstraint(f"compliance IN {ratings}", name="ck_deployment_compliance"),
        sa.ForeignKeyConstraint(
            ["business_case_id"], ["business_cases.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "business_case_id", "option", name="uq_deployment_assessments_case_option"
        ),
    )

    op.create_table(
        "account_briefs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("business_case_id", sa.Uuid(), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column("customer_context", sa.Text(), nullable=False),
        sa.Column("confirmed_needs_summary", sa.Text(), nullable=False),
        sa.Column("solution_summary", sa.Text(), nullable=False),
        sa.Column("poc_summary", sa.Text(), nullable=False),
        sa.Column("roi_summary", sa.Text(), nullable=False),
        sa.Column("deployment_summary", sa.Text(), nullable=False),
        sa.Column("key_risks", sa.JSON(), nullable=False),
        sa.Column("next_steps", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["business_case_id"], ["business_cases.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_case_id", name="uq_account_briefs_case"),
    )


def downgrade() -> None:
    op.drop_table("account_briefs")
    op.drop_table("deployment_assessments")
    op.drop_index("ix_business_cases_account_status", table_name="business_cases")
    op.drop_table("business_cases")
