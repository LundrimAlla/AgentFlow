import pytest

from evaluate_m6 import validate_report


@pytest.mark.parametrize("field", ["dataset_sha256", "model", "implementation_sha256"])
def test_changed_evaluation_version_cannot_reuse_results(field: str) -> None:
    report = {"dataset_sha256": "dataset", "model": "model", "implementation_sha256": "code"}
    validate_report(report, "dataset", "model", "code")
    report[field] = "changed"
    with pytest.raises(SystemExit, match="separate report"):
        validate_report(report, "dataset", "model", "code")


def test_legacy_report_cannot_silently_mix_with_new_prompt() -> None:
    with pytest.raises(SystemExit, match="separate report"):
        validate_report({"dataset_sha256": "dataset", "model": "model"}, "dataset", "model", "code")
