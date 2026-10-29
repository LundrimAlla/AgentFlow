import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Requires migrated test PostgreSQL")
def test_migrated_database_enables_pgvector_and_enforces_rls() -> None:
    engine = create_engine(os.environ["TEST_DATABASE_URL"], connect_args={"connect_timeout": 3})
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            assert (
                connection.execute(
                    text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
                ).scalar_one()
                == "vector"
            )
            assert (
                connection.execute(
                    text(
                        "SELECT relrowsecurity AND relforcerowsecurity FROM pg_class "
                        "WHERE oid = 'knowledge_documents'::regclass"
                    )
                ).scalar_one()
                is True
            )
            # A temporary least-privilege role proves RLS denies reads even with table grants.
            connection.execute(text("CREATE ROLE agentflow_rls_test NOLOGIN"))
            connection.execute(text("GRANT USAGE ON SCHEMA public TO agentflow_rls_test"))
            connection.execute(text("GRANT SELECT ON knowledge_documents TO agentflow_rls_test"))
            connection.execute(
                text(
                    "INSERT INTO knowledge_documents (id, source, title, version, content_hash) "
                    "VALUES (:id, :source, 'Synthetic test', 1, :hash)"
                ),
                {"id": uuid4(), "source": str(uuid4()), "hash": "a" * 64},
            )
            connection.execute(text("SET LOCAL ROLE agentflow_rls_test"))
            assert (
                connection.execute(text("SELECT count(*) FROM knowledge_documents")).scalar() == 0
            )
        finally:
            transaction.rollback()
    engine.dispose()
