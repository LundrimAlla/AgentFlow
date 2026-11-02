from summarize_m6 import summarize


def test_blocked_and_unrun_cases_never_inflate_evaluation_or_latency() -> None:
    cases = [{"category": "knowledge"}, {"category": "unknown"}, {"category": "routing"}]
    rows = [
        {
            "id": "a",
            "category": "knowledge",
            "passed": True,
            "elapsed_ms": 100,
            "checks": {"intent": True},
        },
        {
            "id": "b",
            "category": "unknown",
            "passed": False,
            "elapsed_ms": 99999,
            "error": "budget_exhausted",
        },
    ]
    result = summarize(cases, rows)
    assert result["completed_cases"] == result["blocked_cases"] == result["unattempted_cases"] == 1
    assert result["retrieval_at_5"]["source_recall"] is None
    assert result["observed_latency_ms"]["p95_nearest_rank"] == 100
    assert not result["evaluation_complete"] and not result["release_approved"]
