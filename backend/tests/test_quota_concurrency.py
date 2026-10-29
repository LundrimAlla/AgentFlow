"""Exercise the production Lua reservation against disposable keys in real local Redis."""

import os
import socket
from concurrent.futures import ThreadPoolExecutor
from typing import Any, BinaryIO
from uuid import uuid4

import pytest

from app.live import RESERVE_LUA

pytestmark = pytest.mark.skipif(not os.getenv("TEST_REDIS_PORT"), reason="Requires local Redis")


def read_reply(stream: BinaryIO) -> Any:
    line = stream.readline()
    kind, value = line[:1], line[1:-2]
    if kind == b":":
        return int(value)
    if kind == b"+":
        return value.decode()
    if kind == b"-":
        raise AssertionError(value.decode())
    if kind == b"$":
        length = int(value)
        if length == -1:
            return None
        result = stream.read(length)
        assert stream.read(2) == b"\r\n"
        return result.decode()
    if kind == b"*":
        return [read_reply(stream) for _ in range(int(value))]
    raise AssertionError("Invalid Redis response")


def redis(*parts: object) -> Any:
    encoded = [str(part).encode() for part in parts]
    payload = f"*{len(encoded)}\r\n".encode() + b"".join(
        f"${len(part)}\r\n".encode() + part + b"\r\n" for part in encoded
    )
    with socket.create_connection(("127.0.0.1", int(os.environ["TEST_REDIS_PORT"])), 3) as conn:
        conn.sendall(payload)
        with conn.makefile("rb") as stream:
            return read_reply(stream)


def test_concurrent_reservations_never_overspend_and_rejection_is_atomic() -> None:
    prefix = "{agentflow-test-" + uuid4().hex + "}:"
    requests, tokens = prefix + "requests", prefix + "tokens"
    try:

        def reserve(_: int) -> Any:
            return redis("EVAL", RESERVE_LUA, 2, requests, tokens, 1, 7, 60, 3, 100, 60)

        with ThreadPoolExecutor(max_workers=20) as pool:
            replies = list(pool.map(reserve, range(40)))
        assert sum(reply[0] == 1 for reply in replies) == 7
        assert redis("GET", requests) == "7"
        assert redis("GET", tokens) == "21"
        assert all(reply[1] > 0 for reply in replies if reply[0] == 0)
        assert 0 < redis("TTL", tokens) <= 60
        # Exhaust the second limit while the first would still admit: neither changes.
        assert redis("EVAL", RESERVE_LUA, 2, requests, tokens, 1, 100, 60, 80, 100, 60)[0] == 0
        assert redis("MGET", requests, tokens) == ["7", "21"]
        ttl = redis("TTL", tokens)
        assert redis("EVAL", RESERVE_LUA, 1, tokens, 1, 100, 3600)[0] == 1
        assert redis("TTL", tokens) <= ttl  # Later reservations cannot extend the window.
    finally:
        redis("DEL", requests, tokens)
