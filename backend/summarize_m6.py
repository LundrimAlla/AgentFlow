"""Summarize observed evaluation evidence without counting blocked/unrun cases as passes."""

import json
import math
from pathlib import Path
from typing import Any


def summarize(cases: list[dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [row for row in rows if "error" not in row]
    groups = {}
    for category in ("knowledge", "unknown", "routing", "adversarial"):
        observed = [row for row in completed if row["category"] == category]
        groups[category] = {
            "expected": sum(case["category"] == category for case in cases),
            "completed": len(observed),
            "passed": sum(row["passed"] for row in observed),
        }
    latency = sorted(row["elapsed_ms"] for row in completed)
    ranks = [row["retrieval_at_5"] for row in completed if "retrieval_at_5" in row]
    relevant = sum(rank["expected_source_count"] for rank in ranks)
    matched = sum(rank["matched_expected_sources"] for rank in ranks)
    return {
        "total_cases": len(cases),
        "completed_cases": len(completed),
        "blocked_cases": sum("error" in row for row in rows),
        "unattempted_cases": len(cases) - len({row["id"] for row in rows}),
        "groups": groups,
        "routing_checks": {
            "correct": sum(row["checks"]["intent"] for row in completed),
            "evaluated": len(completed),
        },
        "retrieval_at_5": {
            "instrumented_cases": len(ranks),
            "hit_cases": sum(rank["hit"] for rank in ranks),
            "expected_sources_matched": matched,
            "expected_sources_total": relevant,
            "source_recall": matched / relevant if relevant else None,
            "note": "Expected sources are curated fixture labels; human relevance review pending.",
        },
        "observed_latency_ms": {
            "samples": len(latency),
            "p50_nearest_rank": latency[math.ceil(len(latency) * 0.5) - 1] if latency else None,
            "p95_nearest_rank": latency[math.ceil(len(latency) * 0.95) - 1] if latency else None,
            "note": "Not a warm/cold benchmark. Provider state is uncontrolled; small samples "
            "are not representative latency targets.",
        },
        "evaluation_complete": len(completed) == len(cases),
        "release_approved": False,
    }


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    cases = json.loads((root / "demo-data/m6-evaluation.json").read_text(encoding="utf-8"))
    rows = json.loads((root / "docs/m6-evaluation-result.json").read_text(encoding="utf-8"))[
        "cases"
    ]
    result = summarize(cases, rows)
    (root / "docs/m6-evaluation-summary.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result))
