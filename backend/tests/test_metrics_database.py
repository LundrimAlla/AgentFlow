import asyncio
import os
from uuid import uuid4

import psycopg
import pytest
from psycopg.conninfo import make_conninfo
from test_ingestion_database import database  # noqa: F401

from app.schemas.chat import TraceStep
from app.telemetry import ExecutionMetric, PostgresMetrics

pytestmark = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Requires PostgreSQL")


def test_restricted_metrics_atomic_writes_and_repeatable_retention(database: str) -> None:  # noqa: F811
    # SET ROLE exercises grants and RLS without giving the metrics code operator privileges.
    url = make_conninfo(database, options="-c role=agentflow_metrics")
    store = PostgresMetrics(url)
    metric = ExecutionMetric(
        request_id=uuid4(),
        workflow="chat",
        status_code=200,
        duration_ms=50,
        stages=[TraceStep(agent="router", status="success", duration_ms=40)],
    )
    # Store options are explicit; use a role-specific connection factory in this test.
    original_connect = psycopg.AsyncConnection.connect

    async def restricted_connect(*args: object, **kwargs: object) -> psycopg.AsyncConnection:
        kwargs["options"] = "-c role=agentflow_metrics -c statement_timeout=5000"
        return await original_connect(*args, **kwargs)  # type: ignore[arg-type]

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(psycopg.AsyncConnection, "connect", restricted_connect)
        asyncio.run(store.record(metric))
        # Duplicate stages must roll back the parent row, not leave partial telemetry.
        bad = metric.model_copy(update={"request_id": uuid4(), "stages": metric.stages * 2})
        with pytest.raises(psycopg.errors.UniqueViolation):
            asyncio.run(store.record(bad))
        with psycopg.connect(database) as admin:
            assert admin.execute(
                "SELECT count(*) FROM execution_metrics WHERE request_id=%s", (bad.request_id,)
            ).fetchone() == (0,)
            old_id = uuid4()
            admin.execute(
                "INSERT INTO execution_metrics (request_id, created_at, workflow, status_code, "
                "duration_ms) VALUES (%s, now() - interval '8 days', 'chat', 200, 1)",
                (old_id,),
            )
            admin.execute(
                "INSERT INTO execution_stages VALUES (%s, 'router', 'success', 1)",
                (old_id,),
            )
        assert asyncio.run(store.cleanup()) == 1
        assert asyncio.run(store.cleanup()) == 0
    with psycopg.connect(database) as admin:
        assert admin.execute("SELECT count(*) FROM execution_metrics").fetchone() == (1,)
        assert admin.execute("SELECT count(*) FROM execution_stages").fetchone() == (1,)
    for statement in (
        "SELECT * FROM execution_metrics",
        "SELECT * FROM execution_stages",
        "UPDATE execution_metrics SET duration_ms=0",
        "SELECT * FROM knowledge_sources",
        "INSERT INTO execution_metrics "
        "(request_id, created_at, workflow, status_code, duration_ms) "
        "VALUES (gen_random_uuid(), now() + interval '1 day', 'chat', 200, 1)",
    ):
        with psycopg.connect(url) as restricted:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                restricted.execute(statement)
    with psycopg.connect(url) as restricted:
        assert restricted.execute("DELETE FROM execution_metrics").rowcount == 0
