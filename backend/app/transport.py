"""Bound the raw body before JSON parsing, including chunked uploads."""

import asyncio
from uuid import uuid4

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BoundedBody:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] not in ("/api/chat", "/api/demo/document"):
            await self.app(scope, receive, send)
            return
        request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id

        async def reject(status: int, code: str, message: str) -> None:
            response = JSONResponse(
                {"error": code, "message": message, "request_id": request_id},
                status_code=status,
                headers={"Cache-Control": "no-store"},
            )
            await response(scope, receive, send)

        headers = dict(scope["headers"])
        if headers.get(b"content-encoding", b"identity") != b"identity":
            await reject(
                415, "unsupported_encoding", "Compressed request bodies are not supported."
            )
            return
        body = bytearray()
        try:
            async with asyncio.timeout(5):
                while True:
                    chunk = await receive()
                    if chunk["type"] == "http.disconnect":
                        return
                    data = chunk.get("body", b"")
                    if len(body) + len(data) > 20000:
                        await reject(413, "body_too_large", "Request exceeds the 20 KB limit.")
                        return
                    body.extend(data)
                    if not chunk.get("more_body", False):
                        break
        except TimeoutError:
            await reject(408, "request_timeout", "Request upload took too long.")
            return
        consumed = False

        async def buffered_receive() -> Message:
            nonlocal consumed
            if not consumed:
                consumed = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, buffered_receive, send)
