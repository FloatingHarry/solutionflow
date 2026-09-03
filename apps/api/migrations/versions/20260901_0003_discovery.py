"""Create Phase 3 opportunity and customer discovery tables.

Revision ID: 20260901_0003
Revises: 20260901_0002
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260901_0003"
down_revision: str | None = "20260901_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


hypothesis_statuses = (
    "ai_suggested",
    "user_accepted",
    "user_rejected",
    "need_validation",
    "confirmed",
)
hypothesis_origins = ("manual", "research_template")
confidence_values = ("low", "medium", "high")
review_decisions = ("approve", "reject")


def upgrade() -> None:
    op.create_table(
        "opportunity_hypotheses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("source_claim_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("confidence", sa.String(length=20), nullable=False),
        sa.Column("business_area", sa.String(length=160), nullable=True),
        sa.Column("potential_impact", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=40), server_default="need_validation", nullable=False),
        sa.Column("origin", sa.String(length=40), server_default="manual", nullable=False),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(f"status IN {hypothesis_statuses}", name="ck_hypotheses_status"),
        sa.CheckConstraint(f"origin IN {hypothesis_origins}", name="ck_hypotheses_origin"),
        sa.CheckConstraint(f"confidence IN {confidence_values}", name="ck_hypotheses_confidence"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_claim_id"], ["profile_claims.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id",
            "source_claim_id",
            name="uq_hypotheses_account_source_claim",
        ),
    )
    op.create_index(
        "ix_hypotheses_account_status",
        "opportunity_hypotheses",
        ["account_id", "status"],
    )
    op.create_index(
        "ix_hypotheses_account_created",
        "opportunity_hypotheses",
        ["account_id", "created_at"],
    )

    op.create_table(
        "hypothesis_evidence",
        sa.Column("hypothesis_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["hypothesis_id"], ["opportunity_hypotheses.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("hypothesis_id", "evidence_id"),
    )

    op.create_table(
        "discovery_questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("hypothesis_id", sa.Uuid(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["hypothesis_id"], ["opportunity_hypotheses.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_discovery_questions_account",
        "discovery_questions",
        ["account_id", "created_at"],
    )
    op.create_index(
        "ix_discovery_questions_hypothesis_position",
        "discovery_questions",
        ["hypothesis_id", "position"],
    )

    op.create_table(
        "customer_answers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("respondent_name", sa.String(length=160), nullable=True),
        sa.Column("respondent_role", sa.String(length=160), nullable=True),
        sa.Column(
            "answered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["discovery_questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_customer_answers_account", "customer_answers", ["account_id", "answered_at"]
    )
    op.create_index(
        "ix_customer_answers_question", "customer_answers", ["question_id", "answered_at"]
    )

    op.create_table(
        "confirmed_needs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("hypothesis_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("business_impact", sa.Text(), nullable=True),
        sa.Column("success_metric", sa.Text(), nullable=False),
        sa.Column("constraints", sa.Text(), nullable=True),
        sa.Column(
            "confirmed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["hypothesis_id"], ["opportunity_hypotheses.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hypothesis_id", name="uq_confirmed_needs_hypothesis"),
    )
    op.create_index("ix_confirmed_needs_account", "confirmed_needs", ["account_id", "confirmed_at"])

    op.create_table(
        "confirmed_need_answers",
        sa.Column("confirmed_need_id", sa.Uuid(), nullable=False),
        sa.Column("customer_answer_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["confirmed_need_id"], ["confirmed_needs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["customer_answer_id"], ["customer_answers.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("confirmed_need_id", "customer_answer_id"),
    )

    op.create_table(
        "discovery_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(f"decision IN {review_decisions}", name="ck_discovery_reviews_decision"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_discovery_reviews_account", "discovery_reviews", ["account_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_discovery_reviews_account", table_name="discovery_reviews")
    op.drop_table("discovery_reviews")
    op.drop_table("confirmed_need_answers")
    op.drop_index("ix_confirmed_needs_account", table_name="confirmed_needs")
    op.drop_table("confirmed_needs")
    op.drop_index("ix_customer_answers_question", table_name="customer_answers")
    op.drop_index("ix_customer_answers_account", table_name="customer_answers")
    op.drop_table("customer_answers")
    op.drop_index("ix_discovery_questions_hypothesis_position", table_name="discovery_questions")
    op.drop_index("ix_discovery_questions_account", table_name="discovery_questions")
    op.drop_table("discovery_questions")
    op.drop_table("hypothesis_evidence")
    op.drop_index("ix_hypotheses_account_created", table_name="opportunity_hypotheses")
    op.drop_index("ix_hypotheses_account_status", table_name="opportunity_hypotheses")
    op.drop_table("opportunity_hypotheses")
