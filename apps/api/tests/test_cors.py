from typing import Any

ORIGIN = "http://localhost:5173"


def test_allowed_origin_gets_cors_headers(make_client: Any) -> None:
    response = make_client().get("/health", headers={"Origin": ORIGIN})
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert "x-request-id" in response.headers["access-control-expose-headers"].lower()


def test_unknown_origin_gets_no_cors_headers(make_client: Any) -> None:
    response = make_client().get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in response.headers


def test_preflight_for_allowed_origin(make_client: Any) -> None:
    response = make_client().options(
        "/health",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGIN


def test_preflight_for_unknown_origin_is_rejected(make_client: Any) -> None:
    response = make_client().options(
        "/health",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 400


def test_credentials_are_never_allowed(make_client: Any) -> None:
    response = make_client().get("/health", headers={"Origin": ORIGIN})
    assert "access-control-allow-credentials" not in response.headers
