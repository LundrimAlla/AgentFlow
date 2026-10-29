"""Operator-only single-call evaluation; normal provider budgets remain enforced."""

import asyncio
import json
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import httpx

from app.core.config import Settings
from app.document import extract_invoice
from app.live import LiveError, LiveServices
from app.schemas.document import DocumentRequest


async def main() -> None:
    settings = Settings()
    if not settings.live_enabled:
        raise SystemExit("Enable live mode before running the provider evaluation.")
    started = perf_counter()
    report: dict[str, object] = {
        "scope": "Real Gemini sample extraction; HTTP admission tested separately",
        "sample_id": "invoice-001",
        "passed": False,
    }
    try:
        async with (
            asyncio.timeout(settings.chat_timeout_seconds),
            httpx.AsyncClient(timeout=12, trust_env=False) as client,
        ):
            await extract_invoice(
                LiveServices(settings, client),
                DocumentRequest(
                    sample_id="invoice-001", turnstile_token="internal-evaluation-only"
                ),
                str(uuid4()),
                0,
            )
        report["passed"] = True
    except (LiveError, TimeoutError) as error:
        report["error"] = error.code if isinstance(error, LiveError) else "request_timeout"
    report["elapsed_ms"] = round((perf_counter() - started) * 1000)
    destination = Path(__file__).resolve().parent.parent / "docs/document-evaluation-result.json"
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))
    if not report["passed"]:
        raise SystemExit("Evaluation failed; no automatic retry.")


if __name__ == "__main__":
    asyncio.run(main())
