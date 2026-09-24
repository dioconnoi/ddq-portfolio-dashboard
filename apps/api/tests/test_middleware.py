import logging
import re
from typing import Any

import pytest
from starlette.requests import Request

from ddq_api.core.middleware import client_ip


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
