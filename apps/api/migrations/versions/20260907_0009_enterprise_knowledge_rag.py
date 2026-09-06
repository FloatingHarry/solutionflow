"""Add enterprise and account knowledge RAG.

Revision ID: 20260907_0009
Revises: 20260903_0008
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "20260907_0009"
down_revision: str | None = "20260903_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=True),
        sa.Column("knowledge_scope", sa.String(length=40), nullable=False),
        sa.Column("document_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("source_file", sa.String(length=500), nullable=False),
        sa.Column("media_type", sa.String(length=160), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("confidentiality", sa.String(length=40), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("industry", sa.String(length=120), nullable=True),
        sa.Column("region", sa.String(length=120), nullable=True),
        sa.Column("product", sa.String(length=160), nullable=True),
        sa.Column("deployment_mode", sa.String(length=120), nullable=True),
        sa.Column("page_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("chunk_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("embedding_provider", sa.String(length=40), nullable=False),
        sa.Column("embedding_model", sa.String(length=160), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "(knowledge_scope = 'account' AND account_id IS NOT NULL) OR "
            "(knowledge_scope = 'enterprise' AND account_id IS NULL)",
            name="ck_knowledge_documents_scope_owner",
        ),
        sa.CheckConstraint(
            "knowledge_scope IN ('account', 'enterprise')",
            name="ck_knowledge_documents_scope",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'superseded', 'archived')",
            name="ck_knowledge_documents_status",
        ),
        sa.CheckConstraint(
            "confidentiality IN ('internal', 'confidential', 'restricted')",
            name="ck_knowledge_documents_confidentiality",
        ),
        sa.CheckConstraint(
            "embedding_provider IN ('local_hash', 'openai')",
            name="ck_knowledge_documents_embedding_provider",
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id",
            "knowledge_scope",
            "source_file",
            "version",
            name="uq_knowledge_document_version",
        ),
    )
    op.create_index(
        "ix_knowledge_documents_scope_status",
        "knowledge_documents",
        ["knowledge_scope", "status"],
    )
    op.create_index(
        "ix_knowledge_documents_account_status",
        "knowledge_documents",
        ["account_id", "status"],
    )
    for column in [
        "account_id",
        "document_type",
        "checksum_sha256",
        "industry",
        "region",
        "product",
        "deployment_mode",
    ]:
        op.create_index(f"ix_knowledge_documents_{column}", "knowledge_documents", [column])

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=True),
        sa.Column("knowledge_scope", sa.String(length=40), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section", sa.String(length=300), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "knowledge_scope IN ('account', 'enterprise')",
            name="ck_knowledge_chunks_scope",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["knowledge_documents.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "position", name="uq_knowledge_chunk_position"),
    )
    op.create_index(
        "ix_knowledge_chunks_account_scope",
        "knowledge_chunks",
        ["account_id", "knowledge_scope"],
    )
    op.create_index(
        "ix_knowledge_chunks_document", "knowledge_chunks", ["document_id", "position"]
    )
    op.create_index("ix_knowledge_chunks_account_id", "knowledge_chunks", ["account_id"])
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_embedding_hnsw ON knowledge_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_search_gin ON knowledge_chunks "
        "USING gin (to_tsvector('simple', search_text))"
    )

    op.create_table(
        "knowledge_queries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=160), nullable=True),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=False),
        sa.Column("retrieval_metadata", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "provider IN ('guided', 'openai')", name="ck_knowledge_queries_provider"
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_knowledge_queries_account_created",
        "knowledge_queries",
        ["account_id", "created_at"],
    )

    op.create_table(
        "knowledge_evidence_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("query_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=True),
        sa.Column("citation_id", sa.String(length=80), nullable=False),
        sa.Column("knowledge_scope", sa.String(length=40), nullable=False),
        sa.Column("source_file", sa.String(length=500), nullable=False),
        sa.Column("document_title", sa.String(length=240), nullable=False),
        sa.Column("document_version", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section", sa.String(length=300), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("retrieval_score", sa.Float(), nullable=False),
        sa.Column("rerank_score", sa.Float(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "knowledge_scope IN ('account', 'enterprise')",
            name="ck_knowledge_candidates_scope",
        ),
        sa.CheckConstraint(
            "status IN ('retrieved', 'reviewed', 'rejected')",
            name="ck_knowledge_candidates_status",
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chunk_id"], ["knowledge_chunks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["query_id"], ["knowledge_queries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("query_id", "citation_id", name="uq_knowledge_candidate_citation"),
    )
    op.create_index(
        "ix_knowledge_candidates_account_created",
        "knowledge_evidence_candidates",
        ["account_id", "created_at"],
    )

    op.add_column("agent_runs", sa.Column("citations", sa.JSON(), nullable=True))
    op.execute("UPDATE agent_runs SET citations = '[]'::json WHERE citations IS NULL")
    op.alter_column("agent_runs", "citations", nullable=False)


def downgrade() -> None:
    op.drop_column("agent_runs", "citations")
    op.drop_index(
        "ix_knowledge_candidates_account_created",
        table_name="knowledge_evidence_candidates",
    )
    op.drop_table("knowledge_evidence_candidates")
    op.drop_index("ix_knowledge_queries_account_created", table_name="knowledge_queries")
    op.drop_table("knowledge_queries")
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_search_gin")
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding_hnsw")
    op.drop_index("ix_knowledge_chunks_account_id", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_document", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_account_scope", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    for column in [
        "deployment_mode",
        "product",
        "region",
        "industry",
        "checksum_sha256",
        "document_type",
        "account_id",
    ]:
        op.drop_index(f"ix_knowledge_documents_{column}", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_account_status", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_scope_status", table_name="knowledge_documents")
    op.drop_table("knowledge_documents")
