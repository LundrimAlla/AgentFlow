"""Isolated disposable PostgreSQL database; never modifies the active development corpus."""

import asyncio
import os
import sys
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql
from sqlalchemy.engine import make_url

from app.ingest import corpus_id, ingest
from app.knowledge import load_corpus
from app.retrieval import PostgresKnowledgeStore

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="Requires test PostgreSQL with CREATE DATABASE permission",
)


@pytest.fixture(scope="module")
def database() -> Iterator[str]:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    base = make_url(os.environ["TEST_DATABASE_URL"]).set(drivername="postgresql")
    name = "agentflow_test_" + uuid4().hex
    admin_url = base.render_as_string(hide_password=False)
    url = base.set(database=name).render_as_string(hide_password=False)
    with psycopg.connect(admin_url, autocommit=True, connect_timeout=3) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    old = os.environ.get("DATABASE_URL")
    try:
        os.environ["DATABASE_URL"] = url.replace("postgresql://", "postgresql+psycopg://", 1)
        command.upgrade(Config("alembic.ini"), "head")
        command.upgrade(Config("alembic.ini"), "head")
        yield url
    finally:
        if old is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = old
        with psycopg.connect(admin_url, autocommit=True, connect_timeout=3) as connection:
            connection.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
            )


def test_atomic_ingestion_idempotence_rollback_and_rls(database: str) -> None:
    async def exercise() -> None:
        chunks = load_corpus(Path("../demo-data/company"))
        calls = 0

        async def embed(text: str) -> list[float]:
            nonlocal calls
            calls += 1
            return [1.0] + [0.0] * 767

        first = await ingest(database, chunks, embed)
        second = await ingest(database, chunks, embed)
        assert first["status"] == "published" and second["embedding_calls"] == 0
        assert calls == len(chunks)
        original = corpus_id(chunks)
        # Invalid persisted content forces a SQL failure after corpus insertion.
        broken = [
            replace(c, text="", chunk_id="f" * 64) if c.source_id == "pricing" else c
            for c in chunks
        ]
        with pytest.raises(psycopg.errors.CheckViolation):
            await ingest(database, broken, embed)
        async with await psycopg.AsyncConnection.connect(database) as connection:
            cursor = await connection.execute("SELECT corpus_id FROM knowledge_active")
            assert (await cursor.fetchone()) == (original,)
            cursor = await connection.execute("SELECT count(*) FROM knowledge_corpora")
            assert (await cursor.fetchone()) == (1,)

        async def fail(text: str) -> list[float]:
            raise RuntimeError("provider failure")

        with pytest.raises(RuntimeError):
            await ingest(database, broken, fail)
        # A valid version change and concurrent publication retain old snapshots.
        updated = [
            replace(c, text=c.text + "\n", end=c.end + 1, chunk_id="e" * 64)
            if c.source_id == "pricing"
            else c
            for c in chunks
        ]
        await asyncio.gather(ingest(database, updated, embed), ingest(database, updated, embed))
        store = PostgresKnowledgeStore(database)
        assert await store.source(original, "pricing") is not None
        assert all(
            c.corpus_id == corpus_id(updated) for c in await store.search([1.0] + [0.0] * 767)
        )
        async with await psycopg.AsyncConnection.connect(database) as connection:
            await connection.execute(
                """INSERT INTO knowledge_corpora
                (id, embedding_model, dimensions, chunker_version) VALUES (%s,'test',768,'test')
            """,
                ("d" * 64,),
            )
            await connection.execute("SET LOCAL ROLE agentflow_reader")
            cursor = await connection.execute("SELECT count(*) FROM knowledge_corpora")
            assert (await cursor.fetchone()) == (2,)
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                await connection.execute("DELETE FROM knowledge_active")
            await connection.rollback()

    asyncio.run(exercise())
