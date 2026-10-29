import json
from collections import Counter
from pathlib import Path


def test_m6_dataset_coverage_and_source_expectations() -> None:
    root = Path(__file__).resolve().parents[2]
    cases = json.loads((root / "demo-data/m6-evaluation.json").read_text(encoding="utf-8"))
    assert len(cases) == len({case["id"] for case in cases}) == 40
    assert Counter(case["category"] for case in cases) == {
        "knowledge": 15,
        "unknown": 10,
        "routing": 10,
        "adversarial": 5,
    }
    assert sum(case["split"] == "held_out" for case in cases) == 8
    for case in cases:
        assert 0 < len(case["question"]) <= 2000
        if case["category"] == "knowledge":
            assert case["expected_sources"] and case["expected_terms"]
            sources = "\n".join(
                (root / "demo-data/company" / f"{source}.md").read_text(encoding="utf-8").lower()
                for source in case["expected_sources"]
            )
            assert all(term in sources for term in case["expected_terms"])
