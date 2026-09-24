from typing import Any


def test_requests_over_the_limit_get_429_envelope_with_retry_after(make_client: Any) -> None:
    client = make_client(rate_limit_default="2/minute")
    assert client.get("/health").status_code == 200
    assert client.get("/health").status_code == 200
    limited = client.get("/health")
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "rate_limited"
    assert int(limited.headers["retry-after"]) >= 1


def test_429_still_carries_cors_headers(make_client: Any) -> None:
    client = make_client(rate_limit_default="1/minute")
    origin = {"Origin": "http://localhost:5173"}
    client.get("/health", headers=origin)
    limited = client.get("/health", headers=origin)
    assert limited.status_code == 429
    assert limited.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_buckets_are_per_client_behind_a_trusted_proxy(make_client: Any) -> None:
    client = make_client(rate_limit_default="1/minute", trusted_proxy_hops=1)
    a = {"X-Forwarded-For": "203.0.113.1"}
    b = {"X-Forwarded-For": "203.0.113.2"}
    assert client.get("/health", headers=a).status_code == 200
    assert client.get("/health", headers=a).status_code == 429
    assert client.get("/health", headers=b).status_code == 200


def test_spoofed_leftmost_forwarded_entries_do_not_evade_the_limit(make_client: Any) -> None:
    """Review focus 5."""
    client = make_client(rate_limit_default="1/minute", trusted_proxy_hops=1)
    first = client.get("/health", headers={"X-Forwarded-For": "1.1.1.1, 203.0.113.9"})
    assert first.status_code == 200
    spoofed = client.get("/health", headers={"X-Forwarded-For": "2.2.2.2, 203.0.113.9"})
    assert spoofed.status_code == 429


def test_forwarded_header_is_ignored_when_no_proxy_is_trusted(make_client: Any) -> None:
    client = make_client(rate_limit_default="1/minute", trusted_proxy_hops=0)
    assert client.get("/health", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 200
    assert client.get("/health", headers={"X-Forwarded-For": "2.2.2.2"}).status_code == 429
