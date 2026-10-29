"""Provision only the local AgentFlow read-only login; never print credentials."""

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
        raise ValueError("This helper is restricted to the local AgentFlow database")
    password = values.get("KNOWLEDGE_READER_PASSWORD") or secrets.token_hex(32)
    if url.host == "localhost":
        url = url.set(host="127.0.0.1")
    with psycopg.connect(
        url.render_as_string(hide_password=False), connect_timeout=3
    ) as connection:
        connection.execute("""DO $$ BEGIN
          IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'agentflow_runtime') THEN
            CREATE ROLE agentflow_runtime LOGIN;
          END IF;
        END $$""")
        connection.execute(
            sql.SQL("""ALTER ROLE agentflow_runtime WITH LOGIN PASSWORD {}
            NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 10
        """).format(sql.Literal(password))
        )
        connection.execute("GRANT agentflow_reader TO agentflow_runtime")
        connection.execute("ALTER ROLE agentflow_runtime SET default_transaction_read_only = on")
        connection.execute("ALTER ROLE agentflow_runtime SET statement_timeout = '3s'")
    reader = url.set(username="agentflow_runtime", password=password)
    set_key(path, "KNOWLEDGE_READER_PASSWORD", password)
    set_key(path, "RAG_DATABASE_URL", reader.render_as_string(hide_password=False))
    print("Local read-only database identity configured. Credentials saved privately.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        raise SystemExit(
            "Reader provisioning failed. Check local configuration and migration."
        ) from None
