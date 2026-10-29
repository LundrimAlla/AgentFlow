import json
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError

from app.core.config import Settings
from app.main import create_app


def live_settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        live_enabled=True,
        gemini_api_key=SecretStr("fake-provider-secret"),
        turnstile_secret_key=SecretStr("fake-challenge-secret"),
        upstash_redis_rest_url="https://fixture.upstash.io",
        upstash_redis_rest_token=SecretStr("fake-redis-secret"),
        rate_limit_hmac_secret=SecretStr("a" * 32),
    )


class ExternalServices:
    def __init__(self) -> None:
        self.calls: list[httpx.Request] = []
        self.verify: dict[str, Any] = {"success": True, "hostname": "localhost", "action": "chat"}
        self.redis_status = 200
        self.reservation = [1, 0]
        self.reject_reservation_number = 0
        self.reservation_count = 0
        self.provider_status = 200
        self.provider_timeout = False
        self.intent = "QUOTE_REQUEST"
        self.malformed = False

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        if request.url.host.endswith("upstash.io"):
            self.reservation_count += 1
            if self.reservation_count == self.reject_reservation_number:
                return httpx.Response(200, json={"result": [0, 60]})
            return httpx.Response(self.redis_status, json={"result": self.reservation})
        if request.url.host == "challenges.cloudflare.com":
            return httpx.Response(200, json=self.verify)
        assert request.url.host == "generativelanguage.googleapis.com"
        assert "key=" not in str(request.url)
        assert request.headers["x-goog-api-key"] == "fake-provider-secret"
        if self.provider_timeout:
            raise httpx.ReadTimeout("secret-provider-details", request=request)
        config = json.loads(request.content)["generationConfig"]
        assert config["maxOutputTokens"] == 2048
        assert "tools" not in json.loads(request.content)
        result = {
            "intent": self.intent,
            "lead": {
                "company": "Example Ltd",
                "quantity": 12,
                "customer_type": "B2B",
            },
        }
        if config["responseJsonSchema"]["title"] == "Answer":
            result = {"answer": "AgentFlow demonstrates workflows."}
        text = "invalid secret-provider-details" if self.malformed else json.dumps(result)
        return httpx.Response(
            self.provider_status,
            json={
                "candidates": [
                    {
                        "finishReason": "STOP",
                        "content": {"parts": [{"text": text}]},
                    }
                ]
            },
        )

    def client(self) -> TestClient:
        return TestClient(create_app(live_settings(), transport=httpx.MockTransport(self.handle)))

    @property
    def generations(self) -> int:
        return sum(r.url.host == "generativelanguage.googleapis.com" for r in self.calls)


PAYLOAD = {
    "messages": [{"role": "user", "content": "12 chairs for Example Ltd"}],
    "turnstile_token": "fixture-token",
}


def test_live_lead_has_real_trace_no_fabricated_sources_and_no_persistence() -> None:
    services = ExternalServices()
    response = services.client().post("/api/chat", json=PAYLOAD)
    assert response.status_code == 200
    result = response.json()
    assert result["mode"] == "live" and result["citations"] == []
    assert result["lead"]["quantity"] == 12
    # The provider incorrectly infers B2B from a company name; the server removes it.
    assert result["lead"]["customer_type"] is None
    assert "nothing has been sent" in result["answer"]
    assert services.generations == 1
    assert [s["agent"] for s in result["trace"]] == [
        "safety",
        "router",
        "lead",
        "rag",
        "document",
        "response",
        "validation",
    ]
    assert result["trace"][3]["status"] == "skipped"
    assert response.headers["cache-control"] == "no-store"
    assert "fixture-token" not in response.text


def test_general_question_has_two_reserved_calls() -> None:
    services = ExternalServices()
    services.intent = "GENERAL_QUESTION"
    response = services.client().post("/api/chat", json=PAYLOAD)
    assert response.status_code == 200 and services.generations == 2
    reservations = [json.loads(r.content) for r in services.calls if "upstash" in r.url.host]
    assert len(reservations) == 4
    assert sum("{agentflow-test}:generation:day" in r for r in reservations) == 2


@pytest.mark.parametrize(
    "field,value",
    [
        ("success", False),
        ("success", "true"),
        ("hostname", "evil.example"),
        ("action", "login"),
    ],
)
def test_challenge_rejections_never_reach_gemini(field: str, value: object) -> None:
    services = ExternalServices()
    services.verify[field] = value
    response = services.client().post("/api/chat", json=PAYLOAD)
    assert response.status_code == 403 and services.generations == 0


def test_redis_outage_fails_closed_before_challenge() -> None:
    services = ExternalServices()
    services.redis_status = 503
    response = services.client().post("/api/chat", json=PAYLOAD)
    assert response.status_code == 503 and len(services.calls) == 1


def test_quota_is_not_retried_and_has_retry_after() -> None:
    services = ExternalServices()
    services.reservation = [0, 47]
    response = services.client().post("/api/chat", json=PAYLOAD)
    assert response.status_code == 429 and response.headers["retry-after"] == "47"
    assert len(services.calls) == 1


@pytest.mark.parametrize("failure,status", [("malformed", 502), ("timeout", 504), ("quota", 429)])
def test_provider_failures_are_sanitized_without_retries(failure: str, status: int) -> None:
    services = ExternalServices()
    services.malformed = failure == "malformed"
    services.provider_timeout = failure == "timeout"
    services.provider_status = 429 if failure == "quota" else 200
    response = services.client().post("/api/chat", json=PAYLOAD)
    assert response.status_code == status and services.generations == 1
    assert "secret" not in response.text and "fixture-token" not in response.text


def test_body_limit_applies_without_content_length_and_before_services() -> None:
    services = ExternalServices()
    response = services.client().post("/api/chat", content=iter([b"x" * 10000] * 3))
    assert response.status_code == 413 and services.calls == []


def test_validation_does_not_echo_prompt_or_token() -> None:
    services = ExternalServices()
    response = services.client().post(
        "/api/chat",
        json={
            "messages": [{"role": "system", "content": "private-prompt"}],
            "turnstile_token": "private-token",
        },
    )
    assert response.status_code == 422 and services.calls == []
    assert "private-" not in response.text


def test_forwarded_ip_and_request_id_are_not_trusted() -> None:
    services = ExternalServices()
    response = services.client().post(
        "/api/chat",
        json=PAYLOAD,
        headers={"X-Forwarded-For": "attacker", "X-Request-ID": "attacker"},
    )
    assert response.status_code == 200
    assert response.json()["request_id"] != "attacker"
    assert "attacker" not in services.calls[0].content.decode()
    assert "testclient" not in services.calls[0].content.decode()


def test_live_configuration_rejects_missing_secrets_and_dummy_challenges() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, live_enabled=True)
    data = live_settings().model_dump()
    data["turnstile_secret_key"] = "1x0000000000000000000000000000000AA"
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **data)


@pytest.mark.parametrize("reservation,generations", [(2, 0), (3, 0), (4, 1)])
def test_each_late_budget_rejection_stops_before_the_next_call(
    reservation: int,
    generations: int,
) -> None:
    services = ExternalServices()
    services.intent = "GENERAL_QUESTION"
    services.reject_reservation_number = reservation
    response = services.client().post("/api/chat", json=PAYLOAD)
    assert response.status_code == 429 and services.generations == generations


def test_rejected_duplicate_verification_does_not_call_provider_again() -> None:
    services = ExternalServices()
    client = services.client()
    assert client.post("/api/chat", json=PAYLOAD).status_code == 200
    services.verify = {"success": False, "error-codes": ["timeout-or-duplicate"]}
    assert client.post("/api/chat", json=PAYLOAD).status_code == 403
    assert services.generations == 1


def test_compressed_bodies_are_rejected_before_parsing() -> None:
    services = ExternalServices()
    response = services.client().post(
        "/api/chat", content=b"opaque", headers={"Content-Encoding": "gzip"}
    )
    assert response.status_code == 415 and services.calls == []
