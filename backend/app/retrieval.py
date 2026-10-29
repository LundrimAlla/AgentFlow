"""Read-only pgvector retrieval and immutable public source snapshots."""

import json
import math
from dataclasses import dataclass
from typing import Any, Protocol

import psycopg
from psycopg.rows import dict_row

from app.schemas.chat import SourceDocument

DIMENSIONS = 768
EMBEDDING_MODEL = "gemini-embedding-2"
EMBEDDING_FORMAT = "question-answering-v1"


def normalized_vector(values: Any) -> list[float]:
    if not isinstance(values, list) or len(values) != DIMENSIONS:
        raise ValueError("Invalid embedding dimensions")
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
        raise ValueError("Invalid embedding values")
    norm = math.sqrt(sum(float(v) ** 2 for v in values))
    if not math.isfinite(norm) or norm < 1e-12:
        raise ValueError("Invalid embedding norm")
    return [float(v) / norm for v in values]


@dataclass(frozen=True)
class RetrievedChunk:
    corpus_id: str
    chunk_id: str
    source_id: str
    title: str
    text: str
    first_line: int
    last_line: int
    similarity: float


class KnowledgeStore(Protocol):
    async def search(self, vector: list[float]) -> list[RetrievedChunk]: ...
    async def source(self, corpus_id: str, source_id: str) -> SourceDocument | None: ...


class PostgresKnowledgeStore:
    def __init__(self, url: str):
        self.url = url.replace("postgresql+psycopg://", "postgresql://", 1)

    async def search(self, vector: list[float]) -> list[RetrievedChunk]:
        # Exact cosine search is appropriate for this tiny corpus. No approximate index needed.
        async with await psycopg.AsyncConnection.connect(
            self.url,
            connect_timeout=3,
            options="-c statement_timeout=3000",
            row_factory=dict_row,
        ) as connection:
            cursor = await connection.execute(
                """
                SELECT k.corpus_id, k.chunk_id, k.source_id, s.title, k.content,
                       k.first_line, k.last_line,
                       1 - (k.embedding <=> %s::vector) AS similarity
                FROM knowledge_active a
                JOIN knowledge_corpora c ON c.id = a.corpus_id AND c.published
                JOIN knowledge_chunks k ON k.corpus_id = c.id
                JOIN knowledge_sources s ON s.corpus_id = k.corpus_id AND s.source_id = k.source_id
                WHERE c.embedding_model = %s AND c.dimensions = %s
                ORDER BY k.embedding <=> %s::vector, k.chunk_id LIMIT 4
            """,
                (json.dumps(vector), EMBEDDING_MODEL, DIMENSIONS, json.dumps(vector)),
            )
            rows = await cursor.fetchall()
        return [
            RetrievedChunk(
                corpus_id=row["corpus_id"],
                chunk_id=row["chunk_id"],
                source_id=row["source_id"],
                title=row["title"],
                text=row["content"],
                first_line=row["first_line"],
                last_line=row["last_line"],
                similarity=float(row["similarity"]),
            )
            for row in rows
            if float(row["similarity"]) >= 0.35
        ]

    async def source(self, corpus_id: str, source_id: str) -> SourceDocument | None:
        async with await psycopg.AsyncConnection.connect(
            self.url,
            connect_timeout=3,
            options="-c statement_timeout=3000",
            row_factory=dict_row,
        ) as connection:
            cursor = await connection.execute(
                """
                SELECT s.corpus_id, s.source_id, s.title, s.content
                FROM knowledge_sources s JOIN knowledge_corpora c ON c.id = s.corpus_id
                WHERE s.corpus_id = %s AND s.source_id = %s AND c.published
            """,
                (corpus_id, source_id),
            )
            row = await cursor.fetchone()
        return SourceDocument(**row) if row else None
