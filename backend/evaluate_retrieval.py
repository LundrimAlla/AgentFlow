"""Budgeted integration evaluation using the read-only runtime identity."""

import asyncio
import json
import sys
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import httpx

from app.core.config import Settings
from app.live import LiveError, LiveServices
from app.retrieval import PostgresKnowledgeStore
from app.schemas.chat import ChatRequest, Message


async def main() -> None:
    settings = Settings()
    if not settings.rag_enabled:
        raise ValueError("Activate read-only retrieval before evaluation")
    root = Path(__file__).resolve().parent.parent
    cases = json.loads((root / "demo-data/retrieval-evaluation.json").read_text(encoding="utf-8"))
    report = []
    store = PostgresKnowledgeStore(settings.rag_database_url.get_secret_value())
    async with httpx.AsyncClient(timeout=12, trust_env=False) as client:
        services = LiveServices(settings, client, store)
        for case in cases:
            start = perf_counter()
            try:
                async with asyncio.timeout(settings.chat_timeout_seconds):
                    result = await services.chat(
                        ChatRequest(
                            messages=[Message(role="user", content=case["question"])],
                            turnstile_token="not-used-by-internal-evaluation",
                        ),
                        str(uuid4()),
                    )
            except (LiveError, TimeoutError) as error:
                code = error.code if isinstance(error, LiveError) else "request_timeout"
                report.append(
                    {
                        "id": case["id"],
                        "passed": False,
                        "error": code,
                        "elapsed_ms": round((perf_counter() - start) * 1000),
                    }
                )
                print(json.dumps({"id": case["id"], "passed": False, "error": code}))
                break
            valid = bool(result.citations) == case["expect_citations"]
            valid = valid and all(term in result.answer.lower() for term in case["expected_terms"])
            for citation in result.citations:
                source = await store.source(citation.corpus_id, citation.source_id)
                valid = valid and source is not None and citation.excerpt in source.content
            report.append(
                {
                    "id": case["id"],
                    "passed": valid,
                    "answer": result.answer,
                    "sources": [c.source_id for c in result.citations],
                    "elapsed_ms": round((perf_counter() - start) * 1000),
                }
            )
            print(json.dumps({"id": case["id"], "passed": valid}))
    output = {
        "scope": "Real Gemini + read-only PostgreSQL; admission covered separately",
        "cases": report,
        "all_passed": len(report) == len(cases) and all(row["passed"] for row in report),
    }
    (root / "docs/retrieval-evaluation-result.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8"
    )
    if not output["all_passed"]:
        raise ValueError("Evaluation failed")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(main())
    except Exception:
        raise SystemExit(
            "Evaluation incomplete or failed. Check quotas/configuration; do not retry "
            "automatically. No provider details are logged."
        ) from None
