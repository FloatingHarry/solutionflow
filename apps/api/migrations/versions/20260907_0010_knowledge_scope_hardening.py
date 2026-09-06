"""Harden knowledge namespace ownership constraints.

Revision ID: 20260907_0010
Revises: 20260907_0009
Create Date: 2026-09-07
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260907_0010"
down_revision: str | None = "20260907_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_knowledge_chunks_scope_owner",
        "knowledge_chunks",
        "(knowledge_scope = 'account' AND account_id IS NOT NULL) OR "
        "(knowledge_scope = 'enterprise' AND account_id IS NULL)",
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_knowledge_enterprise_document_version "
        "ON knowledge_documents (source_file, version) "
        "WHERE knowledge_scope = 'enterprise' AND account_id IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_knowledge_enterprise_document_version")
    op.drop_constraint(
        "ck_knowledge_chunks_scope_owner",
        "knowledge_chunks",
        type_="check",
    )
