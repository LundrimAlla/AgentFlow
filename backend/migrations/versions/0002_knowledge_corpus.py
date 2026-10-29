"""Atomic, immutable corpus snapshots and 768-dimensional chunks."""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
          IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'agentflow_reader') THEN
            CREATE ROLE agentflow_reader NOLOGIN;
          END IF;
        END $$;
        CREATE TABLE knowledge_corpora (
          id text PRIMARY KEY CHECK (id ~ '^[a-f0-9]{64}$'),
          embedding_model text NOT NULL,
          dimensions integer NOT NULL CHECK (dimensions = 768),
          chunker_version text NOT NULL,
          published boolean NOT NULL DEFAULT false,
          created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE knowledge_sources (
          corpus_id text NOT NULL REFERENCES knowledge_corpora(id),
          source_id text NOT NULL CHECK (source_id IN
            ('company','products','services','pricing','faq','policies')),
          title text NOT NULL,
          content_hash text NOT NULL,
          content text NOT NULL CHECK (length(content) BETWEEN 1 AND 100000),
          PRIMARY KEY (corpus_id, source_id)
        );
        CREATE TABLE knowledge_chunks (
          corpus_id text NOT NULL,
          chunk_id text NOT NULL,
          source_id text NOT NULL,
          content text NOT NULL CHECK (length(content) BETWEEN 1 AND 1200),
          start_offset integer NOT NULL CHECK (start_offset >= 0),
          end_offset integer NOT NULL CHECK (end_offset > start_offset),
          first_line integer NOT NULL CHECK (first_line > 0),
          last_line integer NOT NULL CHECK (last_line >= first_line),
          embedding vector(768) NOT NULL,
          PRIMARY KEY (corpus_id, chunk_id),
          FOREIGN KEY (corpus_id, source_id) REFERENCES knowledge_sources(corpus_id, source_id)
        );
        CREATE TABLE knowledge_active (
          singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
          corpus_id text NOT NULL REFERENCES knowledge_corpora(id)
        );
        GRANT USAGE ON SCHEMA public TO agentflow_reader;
    """)
    for table in ("knowledge_corpora", "knowledge_sources", "knowledge_chunks", "knowledge_active"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"GRANT SELECT ON {table} TO agentflow_reader")
    op.execute("""
        CREATE POLICY published_corpora ON knowledge_corpora FOR SELECT TO agentflow_reader
          USING (published);
        CREATE POLICY published_sources ON knowledge_sources FOR SELECT TO agentflow_reader
          USING (EXISTS (SELECT 1 FROM knowledge_corpora c
                        WHERE c.id = corpus_id AND c.published));
        CREATE POLICY published_chunks ON knowledge_chunks FOR SELECT TO agentflow_reader
          USING (EXISTS (SELECT 1 FROM knowledge_corpora c
                        WHERE c.id = corpus_id AND c.published));
        CREATE POLICY active_pointer ON knowledge_active
          FOR SELECT TO agentflow_reader USING (true);
    """)


def downgrade() -> None:
    for table in ("knowledge_active", "knowledge_chunks", "knowledge_sources", "knowledge_corpora"):
        op.execute(f"DROP TABLE {table}")
    # The group role can have independently provisioned members; preserve it.
