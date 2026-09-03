"""Create Phase 2 research evidence tables.

Revision ID: 20260901_0002
Revises: 20260901_0001
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260901_0002"
down_revision: str | None = "20260901_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


research_statuses = (
    "queued",
    "running",
    "needs_review",
    "completed",
    "failed",
    "rejected",
)
research_providers = ("mock", "openai")
source_types = (
    "account_input",
    "company_website",
    "annual_report",
    "news",
    "web",
    "other",
)
confidence_values = ("low", "medium", "high")
verification_values = ("direct_input", "ai_extracted", "verified")
review_statuses = ("ai_generated", "human_reviewed", "human_rejected")
profile_sections = (
    "company_overview",
    "products_services",
    "market_geography",
    "customers",
    "recent_developments",
    "financial_operating_signals",
    "ai_digital_initiatives",
    "potential_strategic_priorities",
)


def upgrade() -> None:
    op.create_table(
        "research_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("retry_of_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=40), server_default="queued", nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("provider_response_id", sa.String(length=120), nullable=True),
        sa.Column(
            "query_plan",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(f"status IN {research_statuses}", name="ck_research_runs_status"),
        sa.CheckConstraint(f"provider IN {research_providers}", name="ck_research_runs_provider"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["retry_of_id"], ["research_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_research_runs_account_created",
        "research_runs",
        ["account_id", "created_at"],
    )
    op.create_index("ix_research_runs_account_status", "research_runs", ["account_id", "status"])

    op.create_table(
        "sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("url", sa.String(length=2000), nullable=True),
        sa.Column("publisher", sa.String(length=300), nullable=True),
        sa.Column("published_at", sa.Date(), nullable=True),
        sa.Column(
            "retrieved_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("content_excerpt", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("is_official", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint(f"source_type IN {source_types}", name="ck_sources_source_type"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sources_account_retrieved", "sources", ["account_id", "retrieved_at"])
    op.create_index("ix_sources_run_url", "sources", ["research_run_id", "url"])

    op.create_table(
        "company_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("is_simulated", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("research_run_id", name="uq_company_profiles_research_run"),
    )
    op.create_index(
        "ix_company_profiles_account_created",
        "company_profiles",
        ["account_id", "created_at"],
    )

    op.create_table(
        "evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("supporting_text", sa.Text(), nullable=False),
        sa.Column("locator", sa.String(length=500), nullable=True),
        sa.Column("confidence", sa.String(length=20), nullable=False),
        sa.Column("verification_status", sa.String(length=40), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(f"confidence IN {confidence_values}", name="ck_evidence_confidence"),
        sa.CheckConstraint(
            f"verification_status IN {verification_values}",
            name="ck_evidence_verification_status",
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidence_account_created", "evidence", ["account_id", "created_at"])

    op.create_table(
        "profile_claims",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("section", sa.String(length=80), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("confidence", sa.String(length=20), nullable=False),
        sa.Column("is_inference", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "review_status", sa.String(length=40), server_default="ai_generated", nullable=False
        ),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(f"section IN {profile_sections}", name="ck_profile_claims_section"),
        sa.CheckConstraint(
            f"confidence IN {confidence_values}", name="ck_profile_claims_confidence"
        ),
        sa.CheckConstraint(
            f"review_status IN {review_statuses}", name="ck_profile_claims_review_status"
        ),
        sa.ForeignKeyConstraint(["profile_id"], ["company_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_profile_claims_profile_section", "profile_claims", ["profile_id", "section"]
    )

    op.create_table(
        "claim_evidence",
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["profile_claims.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("claim_id", "evidence_id"),
    )


def downgrade() -> None:
    op.drop_table("claim_evidence")
    op.drop_index("ix_profile_claims_profile_section", table_name="profile_claims")
    op.drop_table("profile_claims")
    op.drop_index("ix_evidence_account_created", table_name="evidence")
    op.drop_table("evidence")
    op.drop_index("ix_company_profiles_account_created", table_name="company_profiles")
    op.drop_table("company_profiles")
    op.drop_index("ix_sources_run_url", table_name="sources")
    op.drop_index("ix_sources_account_retrieved", table_name="sources")
    op.drop_table("sources")
    op.drop_index("ix_research_runs_account_status", table_name="research_runs")
    op.drop_index("ix_research_runs_account_created", table_name="research_runs")
    op.drop_table("research_runs")
