"""Initialize pgvector and synthetic knowledge document metadata.

Vector columns are deferred until the embedding model/dimension is verified.
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("source", "version", name="uq_knowledge_source_version"),
        sa.CheckConstraint("version > 0", name="ck_knowledge_version_positive"),
    )
    op.execute("ALTER TABLE knowledge_documents ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE knowledge_documents FORCE ROW LEVEL SECURITY")
    # No public policies: deny by default. Runtime grants arrive with the ingestion design.


def downgrade() -> None:
    op.drop_table("knowledge_documents")
    # The extension may be shared; never remove it during downgrade.
