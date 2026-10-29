"""Only typed operational metadata crosses this boundary. No payload or exception strings."""

import asyncio
import logging
import sys
from typing import Annotated, Literal, Protocol
from uuid import UUID

import psycopg
from pydantic import Field

from app.core.config import Settings
from app.schemas.chat import Contract, TraceStep


class ExecutionMetric(Contract):
    request_id: UUID
    workflow: Literal["chat", "document"]
    status_code: Annotated[int, Field(ge=200, le=599)]
    duration_ms: Annotated[int, Field(ge=0, le=120000)]
    input_tokens: Annotated[int, Field(ge=0)] | None = None
    output_tokens: Annotated[int, Field(ge=0)] | None = None
    stages: Annotated[list[TraceStep], Field(max_length=7)]


class MetricStore(Protocol):
    async def record(self, metric: ExecutionMetric) -> None: ...


class PostgresMetrics:
    def __init__(self, url: str):
        self.url = url

    async def record(self, metric: ExecutionMetric) -> None:
        async with await psycopg.AsyncConnection.connect(
            self.url, connect_timeout=2, options="-c statement_timeout=500"
        ) as connection:
            await connection.execute(
                "INSERT INTO execution_metrics "
                "(request_id, workflow, status_code, duration_ms, input_tokens, output_tokens) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    metric.request_id,
                    metric.workflow,
                    metric.status_code,
                    metric.duration_ms,
                    metric.input_tokens,
                    metric.output_tokens,
                ),
            )
            for stage in metric.stages:
                await connection.execute(
                    "INSERT INTO execution_stages (request_id, agent, status, duration_ms) "
                    "VALUES (%s, %s, %s, %s)",
                    (metric.request_id, stage.agent, stage.status, stage.duration_ms),
                )

    async def cleanup(self) -> int:
        async with await psycopg.AsyncConnection.connect(
            self.url, connect_timeout=2, options="-c statement_timeout=5000"
        ) as connection:
            result = await connection.execute(
                "DELETE FROM execution_metrics WHERE created_at < now() - interval '7 days'"
            )
            return result.rowcount


async def best_effort_record(store: MetricStore | None, metric: ExecutionMetric) -> None:
    if store is None:
        return
    try:
        async with asyncio.timeout(0.75):
            await store.record(metric)
    except Exception:
        logging.getLogger("uvicorn.error").warning("metrics_write_unavailable")


async def retention_worker(*, once: bool = False) -> None:
    settings = Settings()
    url = settings.telemetry_database_url.get_secret_value()
    if not settings.telemetry_enabled or not url:
        raise SystemExit("Telemetry is disabled or not configured.")
    store = PostgresMetrics(url)
    while True:
        try:
            async with asyncio.timeout(10):
                count = await store.cleanup()
            print(f"metrics_cleanup_success deleted={count}", flush=True)
        except Exception:
            print("metrics_cleanup_failed", flush=True)
            if once:
                raise SystemExit(1) from None
        if once:
            return
        await asyncio.sleep(60)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(retention_worker(once="--once" in sys.argv))
