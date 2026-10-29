import asyncio
import logging
from time import perf_counter
from typing import Annotated, Literal
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI, Request
from fastapi import Path as ApiPath
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.config import Settings
from app.document import extract_invoice
from app.live import LiveError, LiveServices
from app.retrieval import KnowledgeStore, PostgresKnowledgeStore
from app.schemas.chat import ChatRequest, ChatResponse, ErrorResponse, SourceDocument, TraceStep
from app.schemas.document import DocumentRequest, DocumentResponse
from app.telemetry import ExecutionMetric, MetricStore, PostgresMetrics, best_effort_record
from app.transport import BoundedBody


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "0.1.0"


def create_app(
    settings: Settings | None = None,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    store: KnowledgeStore | None = None,
    metrics: MetricStore | None = None,
) -> FastAPI:
    settings = settings or Settings()
    if store is None and settings.rag_enabled:
        store = PostgresKnowledgeStore(settings.rag_database_url.get_secret_value())
    if metrics is None and settings.telemetry_enabled:
        metrics = PostgresMetrics(settings.telemetry_database_url.get_secret_value())

    async def record(
        request_id: str,
        workflow: Literal["chat", "document"],
        started: float,
        status_code: int,
        stages: list[TraceStep],
    ) -> None:
        await best_effort_record(
            metrics,
            ExecutionMetric(
                request_id=UUID(request_id),
                workflow=workflow,
                status_code=status_code,
                duration_ms=min(120000, round((perf_counter() - started) * 1000)),
                stages=stages,
            ),
        )

    api = FastAPI(
        title="AgentFlow API",
        version="0.1.0",
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.app_env != "production" else None,
    )
    api.add_middleware(BoundedBody)
    api.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        expose_headers=["Retry-After"],
    )

    @api.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @api.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            {
                "error": "invalid_request",
                "message": "Check the message format.",
                "request_id": getattr(request.state, "request_id", str(uuid4())),
            },
            status_code=422,
            headers={"Cache-Control": "no-store"},
        )

    # Keep disabled deployments free of live routes and service dependencies.
    if settings.live_enabled:

        @api.post(
            "/api/demo/document",
            response_model=DocumentResponse,
            responses={
                code: {"model": ErrorResponse}
                for code in (403, 408, 413, 415, 422, 429, 502, 503, 504)
            },
        )
        async def document(payload: DocumentRequest, request: Request) -> JSONResponse:
            request_id = request.state.request_id
            started = perf_counter()
            try:
                async with (
                    asyncio.timeout(settings.chat_timeout_seconds),
                    httpx.AsyncClient(
                        timeout=httpx.Timeout(12, connect=3),
                        transport=transport,
                        follow_redirects=False,
                        trust_env=False,
                    ) as client,
                ):
                    services = LiveServices(settings, client, store)
                    peer = request.client.host if request.client else "unknown"
                    await services.admit(payload.turnstile_token, peer)
                    admission_ms = round((perf_counter() - started) * 1000)
                    result = await extract_invoice(services, payload, request_id, admission_ms)
                await record(request_id, "document", started, 200, result.trace)
                return JSONResponse(
                    result.model_dump(mode="json"), headers={"Cache-Control": "no-store"}
                )
            except LiveError as error:
                failure = error
            except TimeoutError:
                failure = LiveError(504, "request_timeout", "Document processing took too long.")
            except Exception:
                failure = LiveError(
                    503, "document_unavailable", "Sample processing is unavailable."
                )
            await record(request_id, "document", started, failure.status, [])
            logging.getLogger("uvicorn.error").warning(
                "document_request_failed request_id=%s code=%s elapsed_ms=%d",
                request_id,
                failure.code,
                round((perf_counter() - started) * 1000),
            )
            headers = {"Cache-Control": "no-store"}
            if failure.retry_after:
                headers["Retry-After"] = str(failure.retry_after)
            return JSONResponse(
                {"error": failure.code, "message": failure.message, "request_id": request_id},
                status_code=failure.status,
                headers=headers,
            )

        @api.post(
            "/api/chat",
            response_model=ChatResponse,
            responses={
                code: {"model": ErrorResponse}
                for code in (403, 408, 413, 415, 422, 429, 502, 503, 504)
            },
        )
        async def chat(payload: ChatRequest, request: Request) -> JSONResponse:
            request_id = request.state.request_id
            started = perf_counter()
            try:
                async with (
                    asyncio.timeout(settings.chat_timeout_seconds),
                    httpx.AsyncClient(
                        timeout=httpx.Timeout(12, connect=3),
                        transport=transport,
                        follow_redirects=False,
                        trust_env=False,
                    ) as client,
                ):
                    services = LiveServices(settings, client, store)
                    # Only the socket peer is trusted; forwarded headers are ignored.
                    peer = request.client.host if request.client else "unknown"
                    admission_started = perf_counter()
                    await services.admit(payload.turnstile_token, peer)
                    admission_ms = round((perf_counter() - admission_started) * 1000)
                    result = await services.chat(payload, request_id)
                    result.trace[0].duration_ms = admission_ms
                await record(request_id, "chat", started, 200, result.trace)
                return JSONResponse(
                    result.model_dump(mode="json"), headers={"Cache-Control": "no-store"}
                )
            except LiveError as error:
                failure = error
            except TimeoutError:
                failure = LiveError(504, "request_timeout", "Live chat took too long.")
            except Exception:
                # Never return/log provider payloads, prompts, tokens or credentials.
                failure = LiveError(
                    503, "live_unavailable", "Live chat is temporarily unavailable."
                )
            await record(request_id, "chat", started, failure.status, [])
            headers = {"Cache-Control": "no-store"}
            logging.getLogger("uvicorn.error").warning(
                "live_request_failed request_id=%s code=%s elapsed_ms=%d",
                request_id,
                failure.code,
                round((perf_counter() - started) * 1000),
            )
            if failure.retry_after:
                headers["Retry-After"] = str(failure.retry_after)
            return JSONResponse(
                {"error": failure.code, "message": failure.message, "request_id": request_id},
                status_code=failure.status,
                headers=headers,
            )

    if settings.rag_enabled:

        @api.get(
            "/api/sources/{corpus_id}/{source_id}",
            response_model=SourceDocument,
            responses={code: {"model": ErrorResponse} for code in (404, 422, 503)},
        )
        async def source(
            corpus_id: Annotated[str, ApiPath(pattern=r"^[a-f0-9]{64}$")],
            source_id: Literal["company", "products", "services", "pricing", "faq", "policies"],
        ) -> JSONResponse:
            request_id = str(uuid4())
            try:
                async with asyncio.timeout(5):
                    document = await store.source(corpus_id, source_id) if store else None
                if document:
                    return JSONResponse(
                        document.model_dump(), headers={"Cache-Control": "public, max-age=3600"}
                    )
                return JSONResponse(
                    {
                        "error": "source_not_found",
                        "message": "Source not found.",
                        "request_id": request_id,
                    },
                    status_code=404,
                )
            except Exception:
                return JSONResponse(
                    {
                        "error": "knowledge_unavailable",
                        "message": "Source is temporarily unavailable.",
                        "request_id": request_id,
                    },
                    status_code=503,
                )

    return api


app = create_app()
