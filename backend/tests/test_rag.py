import json
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from test_live import PAYLOAD, ExternalServices, live_settings

from app.grounding import ABSTENTION, Evidence, GroundedSelection, validate_evidence
from app.main import create_app
from app.retrieval import RetrievedChunk, normalized_vector
from app.schemas.chat import SourceDocument

QUOTE = "There is no published price list."
CHUNK = RetrievedChunk("a" * 64, "b" * 64, "pricing", "Pricing", "# Pricing\n\n" + QUOTE, 1, 3, 0.8)


class Store:
    def __init__(self, chunks: list[RetrievedChunk] | None = None, fail: bool = False):
        self.chunks = [CHUNK] if chunks is None else chunks
        self.fail = fail
        self.searches = 0

    async def search(self, vector: list[float]) -> list[RetrievedChunk]:
        self.searches += 1
        assert len(vector) == 768
        if self.fail:
            raise RuntimeError("private database details")
        return self.chunks

    async def source(self, corpus_id: str, source_id: str) -> SourceDocument | None:
        if self.fail:
            raise RuntimeError("private database details")
        if corpus_id == CHUNK.corpus_id and source_id == CHUNK.source_id:
            return SourceDocument(
                corpus_id=corpus_id, source_id=source_id, title=CHUNK.title, content=CHUNK.text
            )
        return None


class RagServices(ExternalServices):
    def __init__(self) -> None:
        super().__init__()
        self.intent = "KNOWLEDGE_QUERY"
        self.vector: Any = [1.0] + [0.0] * 767
        self.selection: dict[str, Any] = {
            "supported": True,
            "evidence": [{"chunk_id": CHUNK.chunk_id, "quote": QUOTE}],
        }

    def handle(self, request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(":embedContent"):
            self.calls.append(request)
            assert json.loads(request.content)["outputDimensionality"] == 768
            return httpx.Response(200, json={"embedding": {"values": self.vector}})
        if request.url.path.endswith(":generateContent"):
            schema = json.loads(request.content)["generationConfig"]["responseJsonSchema"]
            if schema["title"] == "GroundedSelection":
                self.calls.append(request)
                return httpx.Response(
                    200,
                    json={
                        "candidates": [
                            {
                                "finishReason": "STOP",
                                "content": {"parts": [{"text": json.dumps(self.selection)}]},
                            }
                        ]
                    },
                )
        return super().handle(request)

    def rag_client(self, store: Store) -> TestClient:
        settings = live_settings().model_copy(
            update={"rag_enabled": True, "rag_database_url": SecretStr("postgresql://unused")}
        )
        return TestClient(
            create_app(settings, store=store, transport=httpx.MockTransport(self.handle))
        )


def test_rag_response_has_verified_citations_and_inspectable_source() -> None:
    services, store = RagServices(), Store()
    client = services.rag_client(store)
    response = client.post("/api/chat", json=PAYLOAD)
    assert response.status_code == 200
    result = response.json()
    assert QUOTE in result["answer"] and "[1]" in result["answer"]
    assert result["citations"][0]["first_line"] == 3
    assert result["trace"][3]["status"] == "success"
    source = client.get(f"/api/sources/{CHUNK.corpus_id}/pricing")
    assert source.status_code == 200 and QUOTE in source.json()["content"]
    assert store.searches == 1
    assert sum(r.url.path.endswith(":generateContent") for r in services.calls) == 2
    assert sum(r.url.path.endswith(":embedContent") for r in services.calls) == 1


@pytest.mark.parametrize(
    "selection",
    [
        {"supported": False, "evidence": []},
        {"supported": True, "evidence": []},
        {"supported": True, "evidence": [{"chunk_id": "c" * 64, "quote": QUOTE}]},
        {
            "supported": True,
            "evidence": [{"chunk_id": "b" * 64, "quote": "The price is exactly 500 euros."}],
        },
    ],
)
def test_unknown_or_invented_evidence_abstains(selection: dict[str, Any]) -> None:
    services = RagServices()
    services.selection = selection
    result = services.rag_client(Store()).post("/api/chat", json=PAYLOAD).json()
    assert result["answer"] == ABSTENTION and result["citations"] == []


def test_empty_retrieval_skips_answer_generation() -> None:
    services = RagServices()
    result = services.rag_client(Store([])).post("/api/chat", json=PAYLOAD).json()
    assert result["answer"] == ABSTENTION
    assert sum(r.url.path.endswith(":generateContent") for r in services.calls) == 1


@pytest.mark.parametrize(
    "vector", [[0.0] * 768, [1.0] * 767, [float("nan")] * 768, [True] * 768, [float("inf")] * 768]
)
def test_invalid_vectors_are_rejected(vector: list[object]) -> None:
    with pytest.raises(ValueError):
        normalized_vector(vector)


def test_bad_embedding_never_reaches_database() -> None:
    services, store = RagServices(), Store()
    services.vector = [1.0] * 4
    response = services.rag_client(store).post("/api/chat", json=PAYLOAD)
    assert response.status_code == 502 and store.searches == 0


def test_database_outage_fails_without_invented_answer_or_details() -> None:
    response = RagServices().rag_client(Store(fail=True)).post("/api/chat", json=PAYLOAD)
    assert response.status_code == 503 and "private" not in response.text


def test_source_identifier_validation_and_missing_snapshot() -> None:
    client = RagServices().rag_client(Store())
    assert client.get("/api/sources/not-a-version/pricing").status_code == 422
    assert client.get(f"/api/sources/{'a' * 64}/private").status_code == 422
    assert client.get(f"/api/sources/{'c' * 64}/pricing").status_code == 404


def test_repeated_citation_rejected_as_a_whole() -> None:
    item = Evidence(chunk_id=CHUNK.chunk_id, quote=QUOTE)
    answer, citations, valid = validate_evidence(
        GroundedSelection(supported=True, evidence=[item, item]), [CHUNK]
    )
    assert answer == ABSTENTION and citations == [] and not valid
