"""Create Phase 4 solution catalog, matches, and proposals.

Revision ID: 20260902_0004
Revises: 20260901_0003
Create Date: 2026-09-02
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260902_0004"
down_revision: str | None = "20260901_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


proposal_statuses = ("draft", "needs_revision", "accepted", "rejected")
deployment_options = ("saas_api", "eu_cloud", "private_on_premise")


def upgrade() -> None:
    op.create_table(
        "solution_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("target_pain_points", sa.JSON(), nullable=False),
        sa.Column("target_industries", sa.JSON(), nullable=False),
        sa.Column("required_data", sa.JSON(), nullable=False),
        sa.Column("architecture", sa.Text(), nullable=False),
        sa.Column("deployment_options", sa.JSON(), nullable=False),
        sa.Column("success_metrics", sa.JSON(), nullable=False),
        sa.Column("known_limitations", sa.JSON(), nullable=False),
        sa.Column("estimated_cost_model", sa.Text(), nullable=False),
        sa.Column("example_use_cases", sa.JSON(), nullable=False),
        sa.Column("match_keywords", sa.JSON(), nullable=False),
        sa.Column("is_simulated", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "solution_matches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("confirmed_need_id", sa.Uuid(), nullable=False),
        sa.Column("solution_template_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("matched_terms", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("score >= 0 AND score <= 100", name="ck_solution_matches_score"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["confirmed_need_id"], ["confirmed_needs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["solution_template_id"], ["solution_templates.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "confirmed_need_id",
            "solution_template_id",
            name="uq_solution_matches_need_template",
        ),
    )
    op.create_index(
        "ix_solution_matches_account_score", "solution_matches", ["account_id", "score"]
    )

    op.create_table(
        "solution_proposals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("solution_template_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column("why_fit", sa.Text(), nullable=False),
        sa.Column("architecture", sa.Text(), nullable=False),
        sa.Column("required_data", sa.JSON(), nullable=False),
        sa.Column("model_tool_requirements", sa.JSON(), nullable=False),
        sa.Column("deployment_option", sa.String(length=40), nullable=False),
        sa.Column("security_considerations", sa.JSON(), nullable=False),
        sa.Column("risks", sa.JSON(), nullable=False),
        sa.Column("expected_business_impact", sa.Text(), nullable=False),
        sa.Column("success_metrics", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=40), server_default="draft", nullable=False),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(f"status IN {proposal_statuses}", name="ck_solution_proposals_status"),
        sa.CheckConstraint(
            f"deployment_option IN {deployment_options}",
            name="ck_solution_proposals_deployment",
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["solution_template_id"], ["solution_templates.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_solution_proposals_account_status",
        "solution_proposals",
        ["account_id", "status"],
    )
    op.create_index(
        "ix_solution_proposals_account_created",
        "solution_proposals",
        ["account_id", "created_at"],
    )

    op.create_table(
        "solution_proposal_needs",
        sa.Column("solution_proposal_id", sa.Uuid(), nullable=False),
        sa.Column("confirmed_need_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["solution_proposal_id"], ["solution_proposals.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["confirmed_need_id"], ["confirmed_needs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("solution_proposal_id", "confirmed_need_id"),
    )

    templates = sa.table(
        "solution_templates",
        sa.column("id", sa.Uuid()),
        sa.column("slug", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("target_pain_points", sa.JSON()),
        sa.column("target_industries", sa.JSON()),
        sa.column("required_data", sa.JSON()),
        sa.column("architecture", sa.Text()),
        sa.column("deployment_options", sa.JSON()),
        sa.column("success_metrics", sa.JSON()),
        sa.column("known_limitations", sa.JSON()),
        sa.column("estimated_cost_model", sa.Text()),
        sa.column("example_use_cases", sa.JSON()),
        sa.column("match_keywords", sa.JSON()),
        sa.column("is_simulated", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
        sa.column("version", sa.Integer()),
    )
    op.bulk_insert(
        templates,
        [
            {
                "id": uuid.UUID("10000000-0000-4000-8000-000000000001"),
                "slug": "enterprise-knowledge-assistant",
                "name": "Enterprise Knowledge Assistant",
                "description": "Retrieval-augmented assistant for approved internal knowledge.",
                "target_pain_points": [
                    "slow internal knowledge retrieval",
                    "fragmented policy and procedure documents",
                    "inconsistent answers without citations",
                ],
                "target_industries": ["cross-industry", "regulated industries"],
                "required_data": [
                    "approved internal documents",
                    "document access-control metadata",
                    "representative employee questions",
                ],
                "architecture": (
                    "Ingestion → access-aware index → retrieval → grounded generation → citations"
                ),
                "deployment_options": deployment_options,
                "success_metrics": ["task success rate", "citation accuracy", "time to answer"],
                "known_limitations": [
                    "answer quality depends on source freshness",
                    "document permissions must be mapped correctly",
                ],
                "estimated_cost_model": "Usage-based inference plus indexed document volume.",
                "example_use_cases": ["policy assistant", "technical knowledge search"],
                "match_keywords": [
                    "knowledge",
                    "policy",
                    "search",
                    "retrieval",
                    "documents",
                    "citations",
                    "answer",
                ],
                "is_simulated": True,
                "is_active": True,
                "version": 1,
            },
            {
                "id": uuid.UUID("10000000-0000-4000-8000-000000000002"),
                "slug": "customer-service-copilot",
                "name": "Customer Service Copilot",
                "description": "Agent-assist workspace for service context and response guidance.",
                "target_pain_points": [
                    "high support handling time",
                    "inconsistent service responses",
                    "manual escalation and agent handoffs",
                ],
                "target_industries": ["retail", "telecommunications", "financial services"],
                "required_data": [
                    "resolved support conversations",
                    "service knowledge articles",
                    "ticket metadata",
                ],
                "architecture": (
                    "CRM context → summary and intent → grounded response → agent approval"
                ),
                "deployment_options": ["saas_api", "eu_cloud"],
                "success_metrics": [
                    "handling time",
                    "first-contact resolution",
                    "agent acceptance",
                ],
                "known_limitations": [
                    "customer-facing messages require agent approval",
                    "integration effort varies by CRM",
                ],
                "estimated_cost_model": "Per assisted conversation plus integration costs.",
                "example_use_cases": [
                    "ticket summary",
                    "next-best response",
                    "escalation guidance",
                ],
                "match_keywords": [
                    "customer",
                    "support",
                    "service",
                    "agent",
                    "ticket",
                    "response",
                    "escalation",
                ],
                "is_simulated": True,
                "is_active": True,
                "version": 1,
            },
            {
                "id": uuid.UUID("10000000-0000-4000-8000-000000000003"),
                "slug": "sales-account-copilot",
                "name": "Sales / Account Copilot",
                "description": "Research and preparation assistant for account teams.",
                "target_pain_points": [
                    "slow account research and meeting preparation",
                    "fragmented stakeholder context",
                    "manual proposal preparation",
                ],
                "target_industries": [
                    "B2B technology",
                    "professional services",
                    "industrial sales",
                ],
                "required_data": [
                    "account records",
                    "approved product materials",
                    "meeting notes and research sources",
                ],
                "architecture": (
                    "CRM and research → evidence graph → planning copilot → human-approved brief"
                ),
                "deployment_options": ["saas_api", "eu_cloud"],
                "success_metrics": ["preparation time", "evidence coverage", "seller adoption"],
                "known_limitations": [
                    "recommendations depend on CRM quality",
                    "copilot must not autonomously contact customers",
                ],
                "estimated_cost_model": "Per account workspace plus connector usage.",
                "example_use_cases": [
                    "account brief",
                    "meeting preparation",
                    "opportunity planning",
                ],
                "match_keywords": [
                    "sales",
                    "account",
                    "research",
                    "meeting",
                    "stakeholder",
                    "proposal",
                    "crm",
                ],
                "is_simulated": True,
                "is_active": True,
                "version": 1,
            },
            {
                "id": uuid.UUID("10000000-0000-4000-8000-000000000004"),
                "slug": "document-intelligence",
                "name": "Document Intelligence",
                "description": "Human-in-the-loop extraction, validation, and workflow automation.",
                "target_pain_points": [
                    "manual document and spreadsheet handoffs",
                    "slow data extraction and validation",
                    "repetitive routing workflows",
                ],
                "target_industries": ["logistics", "insurance", "financial operations"],
                "required_data": [
                    "representative document samples",
                    "target extraction schema",
                    "exception and validation rules",
                ],
                "architecture": (
                    "Intake → OCR and layout → extraction → validation → "
                    "human exception queue → export"
                ),
                "deployment_options": deployment_options,
                "success_metrics": [
                    "field extraction accuracy",
                    "straight-through processing",
                    "processing lead time",
                ],
                "known_limitations": [
                    "new layouts require evaluation samples",
                    "low-confidence fields require human review",
                ],
                "estimated_cost_model": "Per processed page plus review and hosting costs.",
                "example_use_cases": [
                    "invoice extraction",
                    "shipping document processing",
                    "spreadsheet workflow automation",
                ],
                "match_keywords": [
                    "document",
                    "spreadsheet",
                    "handoff",
                    "extraction",
                    "routing",
                    "workflow",
                    "manual",
                ],
                "is_simulated": True,
                "is_active": True,
                "version": 1,
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("solution_proposal_needs")
    op.drop_index("ix_solution_proposals_account_created", table_name="solution_proposals")
    op.drop_index("ix_solution_proposals_account_status", table_name="solution_proposals")
    op.drop_table("solution_proposals")
    op.drop_index("ix_solution_matches_account_score", table_name="solution_matches")
    op.drop_table("solution_matches")
    op.drop_table("solution_templates")
