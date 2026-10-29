"""Provision a separate restricted local metrics identity without exposing secrets."""

import secrets
from pathlib import Path

import psycopg
from dotenv import dotenv_values, set_key
from psycopg import sql
from sqlalchemy.engine import make_url


def main() -> None:
    path = Path(__file__).resolve().parent.parent / ".env"
    values = dotenv_values(path)
    url = make_url(values["DATABASE_URL"] or "").set(drivername="postgresql")
    if url.host not in ("localhost", "127.0.0.1") or url.database != "agentflow":
        raise ValueError("Only the local AgentFlow database is supported")
    url = url.set(host="127.0.0.1")
    password = values.get("METRICS_WRITER_PASSWORD") or secrets.token_hex(32)
    with psycopg.connect(url.render_as_string(hide_password=False), connect_timeout=3) as conn:
        conn.execute("""DO $$ BEGIN
          IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'agentflow_telemetry') THEN
            CREATE ROLE agentflow_telemetry LOGIN;
          END IF;
        END $$""")
        conn.execute(
            sql.SQL("""ALTER ROLE agentflow_telemetry WITH LOGIN PASSWORD {}
          NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 5
        """).format(sql.Literal(password))
        )
        conn.execute("GRANT agentflow_metrics TO agentflow_telemetry")
        conn.execute("ALTER ROLE agentflow_telemetry SET statement_timeout = '5s'")
    runtime = url.set(username="agentflow_telemetry", password=password)
    set_key(path, "METRICS_WRITER_PASSWORD", password)
    set_key(path, "TELEMETRY_DATABASE_URL", runtime.render_as_string(hide_password=False))
    set_key(path, "TELEMETRY_ENABLED", "true")
    print("Restricted local metrics identity configured; credentials saved privately.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        raise SystemExit(
            "Metrics provisioning failed; check migrations and local configuration."
        ) from None
