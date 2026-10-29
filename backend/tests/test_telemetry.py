import asyncio
import logging

import httpx
import pytest
from fastapi.testclient import TestClient
from test_document import PAYLOAD as DOCUMENT_PAYLOAD
from test_document import InvoiceServices
from test_live import PAYLOAD, ExternalServices, live_settings

from app.main import create_app
from app.telemetry import ExecutionMetric


class Capture:
    def __init__(self, failure: str = "") -> None:
        self.records: list[ExecutionMetric] = []
        self.failure = failure

    async def record(self, metric: ExecutionMetric) -> None:
        if self.failure == "exception":
            raise RuntimeError("private-password-and-message")
        if self.failure == "stall":
            await asyncio.sleep(10)
        self.records.append(metric)


@pytest.mark.parametrize("document", [False, True])
def test_metadata_excludes_payloads_and_preserves_unknown_token_counts(document: bool) -> None:
    external = InvoiceServices() if document else ExternalServices()
    capture = Capture()
    client = TestClient(
        create_app(
            live_settings(),
            transport=httpx.MockTransport(external.handle),
            metrics=capture,
        )
    )
    response = client.post(
        "/api/demo/document" if document else "/api/chat",
        json=DOCUMENT_PAYLOAD if document else PAYLOAD,
    )
    assert response.status_code == 200 and len(capture.records) == 1
    metric = capture.records[0]
    assert str(metric.request_id) == response.json()["request_id"]
    assert metric.input_tokens is None and metric.output_tokens is None
    assert metric.status_code == 200 and metric.stages
    assert metric.workflow == ("document" if document else "chat")
    serialized = metric.model_dump_json()
    for secret in ("Example", "fixture-token", "fake-provider-secret", "Alpine", "chairs"):
        assert secret not in serialized
    assert set(metric.model_dump()) == {
        "request_id",
        "workflow",
        "status_code",
        "duration_ms",
        "input_tokens",
        "output_tokens",
        "stages",
    }


@pytest.mark.parametrize("failure", ["exception", "stall"])
def test_observability_outage_does_not_fail_answer_or_leak_exception(
    failure: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    external = ExternalServices()
    client = TestClient(
        create_app(
            live_settings(),
            transport=httpx.MockTransport(external.handle),
            metrics=Capture(failure),
        )
    )
    with caplog.at_level(logging.WARNING, logger="uvicorn.error"):
        response = client.post("/api/chat", json=PAYLOAD)
    assert response.status_code == 200
    assert "metrics_write_unavailable" in caplog.text
    assert "private-password-and-message" not in caplog.text


def test_failed_admission_records_status_without_fabricated_stages() -> None:
    external = ExternalServices()
    external.verify["success"] = False
    capture = Capture()
    client = TestClient(
        create_app(
            live_settings(),
            transport=httpx.MockTransport(external.handle),
            metrics=capture,
        )
    )
    assert client.post("/api/chat", json=PAYLOAD).status_code == 403
    assert capture.records[0].status_code == 403
    assert capture.records[0].stages == []
