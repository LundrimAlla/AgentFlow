import asyncio
import logging

import httpx
import pytest
from fastapi.testclient import TestClient
from test_live import PAYLOAD, ExternalServices, live_settings

from app.main import create_app


def test_generation_has_a_bounded_dedicated_timeout() -> None:
    services = ExternalServices()
    settings = live_settings()
    client = TestClient(create_app(settings, transport=httpx.MockTransport(services.handle)))
    assert client.post("/api/chat", json=PAYLOAD).status_code == 200
    generation = next(r for r in services.calls if r.url.path.endswith(":generateContent"))
    assert generation.extensions["timeout"]["read"] == 25
    assert generation.extensions["timeout"]["connect"] == 3


def test_overall_deadline_cancels_service_and_logs_only_metadata(
    caplog: pytest.LogCaptureFixture,
) -> None:
    calls = 0
    cancelled = False

    async def stalled(request: httpx.Request) -> httpx.Response:
        nonlocal calls, cancelled
        calls += 1
        try:
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            cancelled = True
            raise
        return httpx.Response(200, json={"result": [1, 0]})

    settings = live_settings().model_copy(update={"chat_timeout_seconds": 0.03})
    client = TestClient(create_app(settings, transport=httpx.MockTransport(stalled)))
    with caplog.at_level(logging.WARNING, logger="uvicorn.error"):
        response = client.post("/api/chat", json=PAYLOAD)
    assert response.status_code == 504
    assert response.json()["error"] == "request_timeout"
    assert cancelled and calls == 1
    assert response.json()["request_id"] in caplog.text
    assert "fixture-token" not in caplog.text and "Example Ltd" not in caplog.text
    assert "fake-provider-secret" not in caplog.text
