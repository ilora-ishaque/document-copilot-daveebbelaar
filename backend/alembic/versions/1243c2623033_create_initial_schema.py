"""create initial schema

Revision ID: 1243c2623033
Revises:
Create Date: 2026-09-19 20:43:34.067074

"""
from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1243c2623033'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIMENSIONS = 1536


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["id"], ["auth.users.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "chat_threads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["profiles.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_chat_threads_user_id", "chat_threads", ["user_id"])

    op.create_table(
        "chat_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("thread_id", UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("parts", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], ["chat_threads.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_chat_messages_thread_id", "chat_messages", ["thread_id"])

    op.create_table(
        "source_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("ticker", sa.String(), nullable=False),
        sa.Column("company_name", sa.String(), nullable=False),
        sa.Column("filing_type", sa.String(), nullable=False),
        sa.Column("filing_date", sa.Date(), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("accession_number", sa.String(), nullable=False, unique=True),
        sa.Column("source_url", sa.String(), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_source_documents_ticker", "source_documents", ["ticker"])

    op.create_table(
        "document_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("section", sa.String(), nullable=True),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSIONS), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["source_documents.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])

    # Generated column + search/vector indexes: not representable by SQLAlchemy's
    # Column/Computed rendering for Postgres generated columns and pgvector ops classes,
    # so these are written as explicit DDL per backend/AGENTS.md.
    op.execute(
        "ALTER TABLE document_chunks "
        "ADD COLUMN search_vector tsvector GENERATED ALWAYS AS (to_tsvector('english', \"text\")) STORED"
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_search_vector ON document_chunks USING gin (search_vector)"
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding_hnsw ON document_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "message_citations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("message_id", UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_id", UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["chat_messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_message_citations_message_id", "message_citations", ["message_id"])
    op.create_index("ix_message_citations_chunk_id", "message_citations", ["chunk_id"])

    # Row-level security: analysts only ever see their own threads/messages/citations.
    # source_documents/document_chunks are the shared corpus — readable by any
    # authenticated analyst, written only by the backend's service-role key.
    op.execute("ALTER TABLE profiles ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY profiles_select_own ON profiles FOR SELECT USING (id = auth.uid())"
    )
    op.execute(
        "CREATE POLICY profiles_update_own ON profiles FOR UPDATE USING (id = auth.uid())"
    )

    op.execute("ALTER TABLE chat_threads ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY chat_threads_owner ON chat_threads FOR ALL "
        "USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid())"
    )

    op.execute("ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY chat_messages_owner ON chat_messages FOR ALL USING ("
        "  thread_id IN (SELECT id FROM chat_threads WHERE user_id = auth.uid())"
        ") WITH CHECK ("
        "  thread_id IN (SELECT id FROM chat_threads WHERE user_id = auth.uid())"
        ")"
    )

    op.execute("ALTER TABLE message_citations ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY message_citations_owner ON message_citations FOR SELECT USING ("
        "  message_id IN ("
        "    SELECT cm.id FROM chat_messages cm"
        "    JOIN chat_threads ct ON ct.id = cm.thread_id"
        "    WHERE ct.user_id = auth.uid()"
        "  )"
        ")"
    )

    op.execute("ALTER TABLE source_documents ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY source_documents_read_authenticated ON source_documents "
        "FOR SELECT USING (auth.role() = 'authenticated')"
    )

    op.execute("ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY document_chunks_read_authenticated ON document_chunks "
        "FOR SELECT USING (auth.role() = 'authenticated')"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("message_citations")
    op.drop_table("document_chunks")
    op.drop_table("source_documents")
    op.drop_table("chat_messages")
    op.drop_table("chat_threads")
    op.drop_table("profiles")
    # Extension intentionally left in place — other schema objects may depend on it.
