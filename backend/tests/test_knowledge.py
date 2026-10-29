from pathlib import Path

import pytest

from app.knowledge import SOURCE_IDS, chunk_document, load_corpus


def test_canonical_corpus_has_exact_reconstructable_sources() -> None:
    root = Path(__file__).resolve().parents[2] / "demo-data/company"
    chunks = load_corpus(root)
    assert {chunk.source_id for chunk in chunks} == set(SOURCE_IDS)
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)
    for source in SOURCE_IDS:
        content = (root / f"{source}.md").read_text(encoding="utf-8")
        selected = [chunk for chunk in chunks if chunk.source_id == source]
        assert "".join(chunk.text for chunk in selected) == content
        for chunk in selected:
            assert chunk.text == content[chunk.start : chunk.end]
            assert len(chunk.text) <= 1200
            assert chunk.first_line <= chunk.last_line


def test_chunking_is_stable_across_line_endings_and_changes_on_source_update() -> None:
    content = "# Example\n\n" + ("A bounded paragraph. " * 20 + "\n\n") * 8
    chunks = chunk_document("company", content)
    assert len(chunks) > 1
    assert chunks == chunk_document("company", content.replace("\n", "\r\n"))
    assert "".join(c.text for c in chunks) == content
    assert {c.chunk_id for c in chunks}.isdisjoint(
        c.chunk_id for c in chunk_document("company", content + "Changed.\n")
    )


def test_long_paragraph_is_bounded_without_losing_text() -> None:
    content = "# Example\n\n" + "x" * 5000
    chunks = chunk_document("company", content)
    assert all(len(c.text) <= 1200 for c in chunks)
    assert "".join(c.text for c in chunks) == content


def test_missing_or_unallowlisted_source_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_corpus(tmp_path)
    with pytest.raises(ValueError):
        chunk_document("../private", "# Private")
    with pytest.raises(ValueError):
        chunk_document("company", "No title")
