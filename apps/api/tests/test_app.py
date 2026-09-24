from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ddq_api.core.errors import DomainError, NotFoundError
from ddq_api.routers import health as health_module


def test_health_returns_ok_envelope(make_client: Any) -> None:
    response = make_client().get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert body["data"]["status"] == "ok"
    assert body["data"]["environment"] == "test"
    assert body["data"]["version"]


def test_health_stays_200_when_database_is_down(make_client: Any) -> None:
    """Review focus 3: the host health check must not depend on Postgres."""
    client = make_client(db_error=ConnectionError("db down"))
    assert client.get("/health").status_code == 200


def test_ready_ok_when_database_pings(make_client: Any) -> None:
    response = make_client().get("/ready")
    assert response.status_code == 200
    assert response.json()["data"] == {"status": "ready", "checks": {"database": {"ok": True}}}


def test_ready_returns_503_without_leaking_error_text(make_client: Any) -> None:
    client = make_client(db_error=ConnectionError("password=hunter2 host=internal"))
    response = client.get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "not_ready"
    assert body["data"]["checks"]["database"]["ok"] is False
    assert "hunter2" not in response.text


def test_ready_times_out_slow_database(make_client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health_module, "_DB_TIMEOUT_S", 0.05)
    response = make_client(db_delay=1.0).get("/ready")
    assert response.status_code == 503


def test_unknown_route_uses_envelope(make_client: Any) -> None:
    response = make_client().get("/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_wrong_method_uses_envelope(make_client: Any) -> None:
    response = make_client().delete("/health")
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"


def _client_with_routes(make_client: Any) -> TestClient:
    client: TestClient = make_client()
    app: FastAPI = client.app  # type: ignore[assignment]

    @app.get("/_test/echo/{number}")
    async def echo(number: int) -> dict[str, int]:
        return {"number": number}

    @app.get("/_test/domain")
    async def domain() -> None:
        raise NotFoundError("portfolio not found", details={"id": 7})

    @app.get("/_test/custom")
    async def custom() -> None:
        raise DomainError("bad thing")

    @app.get("/_test/boom")
    async def boom() -> None:
        raise RuntimeError("secret internal detail")

    return client


def test_validation_error_is_422_envelope_without_echoing_input(make_client: Any) -> None:
    response = _client_with_routes(make_client).get("/_test/echo/not-a-number")
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["details"]["errors"][0]["loc"] == ["path", "number"]
    assert "not-a-number" not in response.text


def test_domain_errors_map_to_status_and_code(make_client: Any) -> None:
    client = _client_with_routes(make_client)
    missing = client.get("/_test/domain")
    assert missing.status_code == 404
    assert missing.json()["error"] == {
        "code": "not_found",
        "message": "portfolio not found",
        "details": {"id": 7},
    }
    assert client.get("/_test/custom").status_code == 400


def test_unhandled_exception_is_generic_500(make_client: Any) -> None:
    response = _client_with_routes(make_client).get("/_test/boom")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "secret internal detail" not in response.text
    assert "Traceback" not in response.text
