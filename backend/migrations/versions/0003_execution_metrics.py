"""Content-free execution metrics and restricted seven-day cleanup."""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
          IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'agentflow_metrics') THEN
            CREATE ROLE agentflow_metrics NOLOGIN;
          END IF;
        END $$;
        CREATE TABLE execution_metrics (
          request_id uuid PRIMARY KEY,
          created_at timestamptz NOT NULL DEFAULT now(),
          workflow text NOT NULL CHECK (workflow IN ('chat', 'document')),
          status_code integer NOT NULL CHECK (status_code BETWEEN 200 AND 599),
          duration_ms integer NOT NULL CHECK (duration_ms BETWEEN 0 AND 120000),
          input_tokens integer CHECK (input_tokens >= 0),
          output_tokens integer CHECK (output_tokens >= 0)
        );
        CREATE INDEX execution_metrics_retention ON execution_metrics(created_at);
        CREATE TABLE execution_stages (
          request_id uuid NOT NULL REFERENCES execution_metrics(request_id) ON DELETE CASCADE,
          agent text NOT NULL CHECK (agent IN
            ('safety','router','lead','rag','document','response','validation')),
          status text NOT NULL CHECK (status IN ('success','failed','skipped')),
          duration_ms integer NOT NULL CHECK (duration_ms BETWEEN 0 AND 120000),
          PRIMARY KEY (request_id, agent)
        );
        REVOKE ALL ON execution_metrics, execution_stages FROM PUBLIC;
        GRANT USAGE ON SCHEMA public TO agentflow_metrics;
        GRANT INSERT (request_id, workflow, status_code, duration_ms, input_tokens, output_tokens)
          ON execution_metrics TO agentflow_metrics;
        GRANT INSERT ON execution_stages TO agentflow_metrics;
        GRANT SELECT (created_at), DELETE ON execution_metrics TO agentflow_metrics;
        ALTER TABLE execution_metrics ENABLE ROW LEVEL SECURITY;
        ALTER TABLE execution_metrics FORCE ROW LEVEL SECURITY;
        ALTER TABLE execution_stages ENABLE ROW LEVEL SECURITY;
        ALTER TABLE execution_stages FORCE ROW LEVEL SECURITY;
        CREATE POLICY insert_metrics ON execution_metrics FOR INSERT TO agentflow_metrics
          WITH CHECK (created_at = transaction_timestamp());
        CREATE POLICY insert_stages ON execution_stages FOR INSERT TO agentflow_metrics
          WITH CHECK (true);
        CREATE POLICY expired_metrics_visible ON execution_metrics FOR SELECT TO agentflow_metrics
          USING (created_at < now() - interval '7 days');
        CREATE POLICY delete_expired_metrics ON execution_metrics FOR DELETE TO agentflow_metrics
          USING (created_at < now() - interval '7 days');
    """)


def downgrade() -> None:
    op.execute("DROP TABLE execution_stages; DROP TABLE execution_metrics;")
