"""Resumable bounded live evaluation. Never resets quotas or silently retries cases."""

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import httpx

from app.core.config import Settings
from app.grounding import ABSTENTION
from app.live import Decision, LiveError, LiveServices
from app.retrieval import PostgresKnowledgeStore
from app.schemas.chat import ChatRequest, Contract, Message

ROOT = Path(__file__).resolve().parent.parent


class ObservedServices(LiveServices):
    intent: str | None = None

    async def generate[T: Contract](self, system: str, request: ChatRequest, schema: type[T]) -> T:
        result = await super().generate(system, request, schema)
        if isinstance(result, Decision):
            self.intent = result.intent
        return result


async def main(limit: int, retry_blocked: bool = False) -> None:
    settings = Settings()
    if not settings.rag_enabled:
        raise SystemExit("Live retrieval must be enabled.")
    fixture = ROOT / "demo-data/m6-evaluation.json"
    digest = hashlib.sha256(fixture.read_bytes()).hexdigest()
    cases = json.loads(fixture.read_text(encoding="utf-8"))
    destination = ROOT / "docs/m6-evaluation-result.json"
    report = (
        json.loads(destination.read_text())
        if destination.exists()
        else {
            "dataset_sha256": digest,
            "model": settings.gemini_model,
            "cases": [],
            "scope": "Real provider and read-only retrieval; public admission tested separately",
        }
    )
    if report["dataset_sha256"] != digest or report["model"] != settings.gemini_model:
        raise SystemExit(
            "Dataset/model changed; archive the previous report before a new evaluation."
        )
    if retry_blocked:
        report.setdefault("previous_blocked_attempts", []).extend(
            row for row in report["cases"] if "error" in row
        )
        report["cases"] = [row for row in report["cases"] if "error" not in row]
    completed = {row["id"] for row in report["cases"]}
    store = PostgresKnowledgeStore(settings.rag_database_url.get_secret_value())
    async with httpx.AsyncClient(timeout=12, trust_env=False) as client:
        services = ObservedServices(settings, client, store)
        for case in [c for c in cases if c["id"] not in completed][:limit]:
            started = perf_counter()
            row = {"id": case["id"], "category": case["category"], "split": case["split"]}
            try:
                async with asyncio.timeout(settings.chat_timeout_seconds):
                    result = await services.chat(
                        ChatRequest(
                            messages=[Message(role="user", content=case["question"])],
                            turnstile_token="internal-evaluation-only",
                        ),
                        str(uuid4()),
                    )
                    provenance = True
                    for citation in result.citations:
                        source = await store.source(citation.corpus_id, citation.source_id)
                        provenance &= source is not None and citation.excerpt in source.content
                expected = case["expected_intent"]
                intent_ok = services.intent in (
                    expected if isinstance(expected, list) else [expected]
                )
                sources = {citation.source_id for citation in result.citations}
                source_ok = not case["expected_sources"] or bool(
                    sources.intersection(case["expected_sources"])
                )
                terms_ok = all(term in result.answer.lower() for term in case["expected_terms"])
                lead_ok = case["expected_lead"] is None or (
                    result.lead is not None
                    and all(
                        result.lead.model_dump().get(k) == v
                        for k, v in case["expected_lead"].items()
                    )
                )
                abstention_ok = not case["expect_abstention"] or (
                    not result.citations
                    and (result.answer == ABSTENTION or services.intent == "UNSUPPORTED")
                )
                row.update(
                    passed=all(
                        (provenance, intent_ok, source_ok, terms_ok, lead_ok, abstention_ok)
                    ),
                    checks=dict(
                        provenance=provenance,
                        intent=intent_ok,
                        sources=source_ok,
                        terms=terms_ok,
                        lead=lead_ok,
                        abstention=abstention_ok,
                    ),
                    answer=result.answer,
                    actual_intent=services.intent,
                    sources=sorted(sources),
                )
            except (LiveError, TimeoutError) as error:
                row.update(
                    passed=False,
                    outcome="blocked",
                    error=error.code if isinstance(error, LiveError) else "request_timeout",
                )
            row["elapsed_ms"] = round((perf_counter() - started) * 1000)
            report["cases"].append(row)
            report["updated_at"] = datetime.now(UTC).isoformat()
            report["total_cases"] = len(cases)
            report["attempted_cases"] = len(report["cases"])
            report["completed_cases"] = sum("error" not in r for r in report["cases"])
            report["blocked_cases"] = sum("error" in r for r in report["cases"])
            report["passed_cases"] = sum(r["passed"] for r in report["cases"])
            report["all_passed"] = report["passed_cases"] == len(cases)
            destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({k: row[k] for k in ("id", "passed", "elapsed_ms")}), flush=True)
            if "error" in row:
                break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, choices=range(1, 41), default=4)
    parser.add_argument(
        "--retry-blocked",
        action="store_true",
        help="Explicitly retry operationally blocked cases; retains prior evidence",
    )
    args = parser.parse_args()
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(main(args.limit, args.retry_blocked))
    except Exception:
        raise SystemExit("Evaluation stopped; inspect safe report and configuration.") from None
