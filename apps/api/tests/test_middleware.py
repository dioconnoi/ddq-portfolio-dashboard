import logging
import re
from typing import Any

import pytest
from starlette.requests import Request

from ddq_api.core.middleware import BodySizeLimitMiddleware, client_ip


def _request(
    headers: dict[str, str], client: tuple[str, int] | None = ("10.0.0.1", 1234)
) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": client,
    }
    return Request(scope)


def test_client_ip_ignores_forwarded_header_when_no_trusted_proxy() -> None:
    assert client_ip(_request({"x-forwarded-for": "9.9.9.9"}), hops=0) == "10.0.0.1"


def test_client_ip_takes_entry_appended_by_the_trusted_proxy() -> None:
    """Review focus 5: leftmost entries are attacker-controlled; the rightmost is the proxy's."""
    request = _request({"x-forwarded-for": "6.6.6.6, 9.9.9.9, 1.1.1.1"})
    assert client_ip(request, hops=1) == "1.1.1.1"
    assert client_ip(request, hops=2) == "9.9.9.9"


def test_client_ip_falls_back_when_header_shorter_than_hops() -> None:
    assert client_ip(_request({"x-forwarded-for": "1.1.1.1"}), hops=2) == "10.0.0.1"


def test_client_ip_without_client_is_unknown() -> None:
    assert client_ip(_request({}, client=None), hops=0) == "unknown"


def test_every_response_has_a_request_id(make_client: Any) -> None:
    response = make_client().get("/health")
    assert re.fullmatch(r"[0-9a-f]{32}", response.headers["x-request-id"])


def test_valid_incoming_request_id_is_kept(make_client: Any) -> None:
    response = make_client().get("/health", headers={"X-Request-ID": "trace-abc_12345"})
    assert response.headers["x-request-id"] == "trace-abc_12345"


def test_invalid_incoming_request_id_is_replaced(make_client: Any) -> None:
    response = make_client().get("/health", headers={"X-Request-ID": "bad id with spaces"})
    assert re.fullmatch(r"[0-9a-f]{32}", response.headers["x-request-id"])


def test_security_headers_present(make_client: Any) -> None:
    headers = make_client().get("/health").headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "no-referrer"
    assert headers["cache-control"] == "no-store"
    assert "strict-transport-security" not in headers


def test_hsts_only_in_production(make_client: Any) -> None:
    client = make_client(environment="production", allowed_origins=("https://app.example.com",))
    assert "max-age=" in client.get("/health").headers["strict-transport-security"]


def test_oversized_body_is_rejected_with_413_envelope(make_client: Any) -> None:
    client = make_client(max_request_bytes=1024)
    response = client.post("/health", content=b"x" * 2048)
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


def test_chunked_body_without_length_is_rejected_with_411(make_client: Any) -> None:
    response = make_client().post("/health", content=(chunk for chunk in [b"abc"]))
    assert response.status_code == 411


def test_access_log_records_status_without_query_string(
    make_client: Any, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="ddq_api.access"):
        make_client().get("/health?token=secret")
    contexts = [getattr(r, "ctx", {}) for r in caplog.records if r.name == "ddq_api.access"]
    assert contexts
    assert contexts[-1]["status"] == 200
    assert contexts[-1]["path"] == "/health"
    assert "secret" not in str(contexts)


def _request_multi(pairs: list[tuple[str, str]]) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(k.lower().encode(), v.encode()) for k, v in pairs],
        "client": ("10.0.0.1", 1234),
    }
    return Request(scope)


def test_client_ip_joins_duplicate_forwarded_headers() -> None:
    """Two X-Forwarded-For lines: the proxy's is the LAST entry overall, not the first line."""
    request = _request_multi([("x-forwarded-for", "6.6.6.6"), ("x-forwarded-for", "203.0.113.9")])
    assert client_ip(request, hops=1) == "203.0.113.9"


def test_client_ip_rejects_entries_that_are_not_ip_addresses() -> None:
    assert client_ip(_request({"x-forwarded-for": "not-an-ip"}), hops=1) == "10.0.0.1"
    assert client_ip(_request({"x-forwarded-for": "x" * 5000}), hops=1) == "10.0.0.1"


def test_client_ip_collapses_ipv6_to_its_64_prefix() -> None:
    first = client_ip(_request({"x-forwarded-for": "2001:db8:1:2:aaaa::1"}), hops=1)
    second = client_ip(_request({"x-forwarded-for": "2001:db8:1:2:bbbb::2"}), hops=1)
    assert first == second == "2001:db8:1:2::/64"


async def _body_limit_status(
    headers: list[tuple[bytes, bytes]], method: str = "POST", scope_type: str = "http"
) -> int:
    started: list[int] = []

    async def inner(scope: Any, receive: Any, send: Any) -> None:
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    async def send(message: dict[str, Any]) -> None:
        if message["type"] == "http.response.start":
            started.append(message["status"])

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    scope = {"type": scope_type, "method": method, "headers": headers}
    await BodySizeLimitMiddleware(inner, 1024)(scope, receive, send)
    return started[0]


async def test_body_limit_passes_a_small_declared_body() -> None:
    assert await _body_limit_status([(b"content-length", b"10")]) == 204


async def test_body_limit_rejects_content_length_combined_with_chunked() -> None:
    headers = [(b"content-length", b"1"), (b"transfer-encoding", b"chunked")]
    assert await _body_limit_status(headers) == 400


async def test_body_limit_rejects_chunked_on_any_method() -> None:
    assert await _body_limit_status([(b"transfer-encoding", b"chunked")], method="DELETE") == 411


async def test_body_limit_rejects_non_ascii_digit_lengths_without_crashing() -> None:
    assert await _body_limit_status([(b"content-length", "²".encode())]) == 413


async def test_body_limit_ignores_non_http_scopes() -> None:
    assert await _body_limit_status([], scope_type="websocket") == 204
