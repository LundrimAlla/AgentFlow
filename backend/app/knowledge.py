"""Deterministic local corpus preparation for M4; no provider or database calls."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

SOURCE_IDS = ("company", "products", "services", "pricing", "faq", "policies")
CHUNKER_VERSION = "paragraph-v1"


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    source_id: str
    title: str
    content_hash: str
    text: str
    start: int
    end: int
    first_line: int
    last_line: int


def chunk_document(source_id: str, content: str, maximum: int = 1200) -> list[KnowledgeChunk]:
    if source_id not in SOURCE_IDS:
        raise ValueError("Unknown source identifier")
    if maximum < 100 or maximum > 4000:
        raise ValueError("Chunk size must be between 100 and 4000 characters")
    # All offsets and hashes refer to canonical LF text, independently of checkout OS.
    content = content.replace("\r\n", "\n")
    if not content.startswith("# ") or not content.strip():
        raise ValueError("Source must have a Markdown title")
    title = content.splitlines()[0][2:].strip()
    if not title:
        raise ValueError("Source title cannot be empty")
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    chunks: list[KnowledgeChunk] = []
    start = 0
    while start < len(content):
        end = min(start + maximum, len(content))
        if end < len(content):
            boundary = content.rfind("\n\n", start + maximum // 3, end)
            if boundary != -1:
                end = boundary + 2
        text = content[start:end]
        identity = f"{CHUNKER_VERSION}:{source_id}:{digest}:{start}:{end}"
        chunks.append(
            KnowledgeChunk(
                chunk_id=hashlib.sha256(identity.encode()).hexdigest(),
                source_id=source_id,
                title=title,
                content_hash=digest,
                text=text,
                start=start,
                end=end,
                first_line=content.count("\n", 0, start) + 1,
                last_line=content.count("\n", 0, max(start, end - 1)) + 1,
            )
        )
        start = end
    return chunks


def load_corpus(directory: Path) -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    root = directory.resolve(strict=True)
    for source_id in SOURCE_IDS:
        path = (root / f"{source_id}.md").resolve(strict=True)
        if path.parent != root or path.stat().st_size > 100000:
            raise ValueError("Source must be a bounded file inside the corpus directory")
        chunks.extend(chunk_document(source_id, path.read_text(encoding="utf-8")))
    return chunks
