import httpx
import pytest
from test_live import PAYLOAD
from test_rag import RagServices, Store


@pytest.mark.parametrize("stage", ["verification", "generation", "embedding"])
@pytest.mark.parametrize("failure", ["timeout", "503", "429"])
def test_dependency_failure_stops_workflow_without_retry_or_private_details(
    stage: str,
    failure: str,
) -> None:
    class FailingServices(RagServices):
        attempts = 0

        def handle(self, request: httpx.Request) -> httpx.Response:
            targeted = (
                (stage == "verification" and request.url.host == "challenges.cloudflare.com")
                or (stage == "generation" and request.url.path.endswith(":generateContent"))
                or (stage == "embedding" and request.url.path.endswith(":embedContent"))
            )
            if targeted:
                self.attempts += 1
                self.calls.append(request)
                if failure == "timeout":
                    raise httpx.ReadTimeout("private-provider-secret", request=request)
                return httpx.Response(int(failure), json={"details": "private-provider-secret"})
            return super().handle(request)

    services, store = FailingServices(), Store()
    response = services.rag_client(store).post("/api/chat", json=PAYLOAD)
    expected = (
        503
        if stage == "verification"
        else {
            "timeout": 504,
            "503": 502,
            "429": 429,
        }[failure]
    )
    assert response.status_code == expected
    assert services.attempts == 1 and store.searches == 0
    assert "private-provider-secret" not in response.text
    assert "fixture-token" not in response.text
    assert "answer" not in response.json()
