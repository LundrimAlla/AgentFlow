import json
from typing import Any

import httpx
import pytest
from test_live import ExternalServices

from app.document import SAMPLES

PAYLOAD = {"sample_id": "invoice-001", "turnstile_token": "fixture-token"}


class InvoiceServices(ExternalServices):
    def __init__(self) -> None:
        super().__init__()
        self.invoice: dict[str, Any] = json.loads(
            (SAMPLES / "invoice-001.expected.json").read_text(encoding="utf-8")
        )

    def handle(self, request: httpx.Request) -> httpx.Response:
        if request.url.host != "generativelanguage.googleapis.com":
            return super().handle(request)
        self.calls.append(request)
        body = json.loads(request.content)
        assert body["generationConfig"]["responseJsonSchema"]["title"] == "Invoice"
        assert "SYNTHETIC SAMPLE INVOICE" in body["contents"][0]["parts"][0]["text"]
        assert "fixture-token" not in request.content.decode()
        if self.provider_timeout:
            raise httpx.ReadTimeout("secret-provider-details", request=request)
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "finishReason": "STOP",
                        "content": {"parts": [{"text": json.dumps(self.invoice)}]},
                    }
                ]
            },
        )


def test_extracts_exact_sample_with_one_reserved_generation() -> None:
    services = InvoiceServices()
    response = services.client().post("/api/demo/document", json=PAYLOAD)
    assert response.status_code == 200
    result = response.json()
    assert result["invoice"] == services.invoice
    assert result["mode"] == "live"
    assert [step["agent"] for step in result["trace"]] == ["safety", "document", "validation"]
    assert services.generations == 1 and services.reservation_count == 3
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("sample_id", ["../.env", "https://example.com/invoice", "other", ""])
def test_invalid_ids_rejected_before_file_access_or_external_calls(
    sample_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    services = InvoiceServices()

    def forbidden(*args: Any, **kwargs: Any) -> str:
        pytest.fail("Invalid sample caused a filesystem read")

    monkeypatch.setattr(type(SAMPLES), "read_text", forbidden)
    response = services.client().post(
        "/api/demo/document", json={**PAYLOAD, "sample_id": sample_id}
    )
    assert response.status_code == 422 and services.calls == []
    assert sample_id not in response.text or sample_id == ""


@pytest.mark.parametrize("field,value", [("total_cents", 35701), ("customer", "Invented Ltd")])
def test_incorrect_extraction_is_rejected_without_fixture_fallback(field: str, value: Any) -> None:
    services = InvoiceServices()
    services.invoice[field] = value
    response = services.client().post("/api/demo/document", json=PAYLOAD)
    assert response.status_code == 502
    assert response.json()["error"] == "document_validation_failed"
    assert "invoice" not in response.json()


def test_document_uses_verification_and_shared_budget() -> None:
    services = InvoiceServices()
    services.verify["success"] = False
    assert services.client().post("/api/demo/document", json=PAYLOAD).status_code == 403
    assert services.generations == 0
    services = InvoiceServices()
    services.reject_reservation_number = 3
    response = services.client().post("/api/demo/document", json=PAYLOAD)
    assert response.status_code == 429 and services.generations == 0
    assert response.headers["retry-after"] == "60"


def test_document_timeout_is_sanitized_and_not_retried() -> None:
    services = InvoiceServices()
    services.provider_timeout = True
    response = services.client().post("/api/demo/document", json=PAYLOAD)
    assert response.status_code == 504 and services.generations == 1
    assert "secret-provider-details" not in response.text


def test_document_body_is_bounded() -> None:
    services = InvoiceServices()
    response = services.client().post("/api/demo/document", content="x" * 20001)
    assert response.status_code == 413 and not services.calls
