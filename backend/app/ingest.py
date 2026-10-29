"""Operator-only ingestion. Run from backend: python -m app.ingest [--dry-run]."""

import argparse
import asyncio
import hashlib
import json
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path

import httpx
import psycopg

from app.core.config import Settings
from app.knowledge import CHUNKER_VERSION, SOURCE_IDS, KnowledgeChunk, load_corpus
from app.retrieval import DIMENSIONS, EMBEDDING_FORMAT, EMBEDDING_MODEL, normalized_vector

Embed = Callable[[str], Awaitable[list[float]]]


def corpus_id(chunks: list[KnowledgeChunk]) -> str:
    identity = [EMBEDDING_MODEL, EMBEDDING_FORMAT, str(DIMENSIONS), CHUNKER_VERSION]
    identity.extend(chunk.chunk_id for chunk in chunks)
    return hashlib.sha256("\n".join(identity).encode()).hexdigest()


async def ingest(url: str, chunks: list[KnowledgeChunk], embed: Embed) -> dict[str, str | int]:
    if not chunks or len(chunks) > 32 or {c.source_id for c in chunks} != set(SOURCE_IDS):
        raise ValueError("A complete corpus of at most 32 chunks is required")
    url = url.replace("postgresql+psycopg://", "postgresql://", 1)
    version = corpus_id(chunks)
    async with await psycopg.AsyncConnection.connect(url, connect_timeout=3) as connection:
        cursor = await connection.execute(
            "SELECT id FROM knowledge_corpora WHERE id = %s AND published", (version,)
        )
        exists = await cursor.fetchone() is not None
    # No database transaction is held during provider calls. All must succeed first.
    vectors = [] if exists else [normalized_vector(await embed(c.text)) for c in chunks]
    async with await psycopg.AsyncConnection.connect(
        url,
        connect_timeout=3,
        options="-c statement_timeout=10000",
    ) as connection:
        await connection.execute("SELECT pg_advisory_xact_lock(7042026)")
        cursor = await connection.execute(
            "SELECT id FROM knowledge_corpora WHERE id = %s AND published", (version,)
        )
        already_published = await cursor.fetchone() is not None
        if not already_published:
            if len(vectors) != len(chunks):
                raise ValueError("Corpus disappeared during ingestion")
            await connection.execute(
                """
                INSERT INTO knowledge_corpora (id, embedding_model, dimensions, chunker_version)
                VALUES (%s, %s, %s, %s)
            """,
                (version, EMBEDDING_MODEL, DIMENSIONS, CHUNKER_VERSION),
            )
            for source in SOURCE_IDS:
                selected = [c for c in chunks if c.source_id == source]
                await connection.execute(
                    """
                    INSERT INTO knowledge_sources
                        (corpus_id, source_id, title, content_hash, content)
                    VALUES (%s, %s, %s, %s, %s)
                """,
                    (
                        version,
                        source,
                        selected[0].title,
                        selected[0].content_hash,
                        "".join(c.text for c in selected),
                    ),
                )
            for chunk, vector in zip(chunks, vectors, strict=True):
                await connection.execute(
                    """
                    INSERT INTO knowledge_chunks
                      (corpus_id, chunk_id, source_id, content, start_offset, end_offset,
                       first_line, last_line, embedding)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::vector)
                """,
                    (
                        version,
                        chunk.chunk_id,
                        chunk.source_id,
                        chunk.text,
                        chunk.start,
                        chunk.end,
                        chunk.first_line,
                        chunk.last_line,
                        json.dumps(vector),
                    ),
                )
            await connection.execute(
                "UPDATE knowledge_corpora SET published = true WHERE id = %s", (version,)
            )
        await connection.execute(
            """
            INSERT INTO knowledge_active(singleton, corpus_id) VALUES (true, %s)
            ON CONFLICT (singleton) DO UPDATE SET corpus_id = EXCLUDED.corpus_id
        """,
            (version,),
        )
        # Context manager commits every table and the active pointer together.
    return {
        "corpus_id": version,
        "chunks": len(chunks),
        "embedding_calls": len(vectors),
        "status": "reused" if already_published else "published",
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=Path("../demo-data/company"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    chunks = load_corpus(args.source_dir)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "corpus_id": corpus_id(chunks),
                    "chunks": len(chunks),
                    "sources": len(SOURCE_IDS),
                    "provider_calls": 0,
                }
            )
        )
        return
    from app.live import LiveServices

    settings = Settings()
    if not settings.live_enabled or not settings.database_url.get_secret_value():
        raise ValueError("Live credentials and operator DATABASE_URL are required")
    async with asyncio.timeout(180), httpx.AsyncClient(timeout=12, trust_env=False) as client:
        services = LiveServices(settings, client)

        async def embed(text: str) -> list[float]:
            return await services.embed(text, purpose="ingest")

        print(json.dumps(await ingest(settings.database_url.get_secret_value(), chunks, embed)))


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(main())
    except Exception:
        print(
            "Ingestion failed; no incomplete corpus was activated. Check configuration and quotas.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
