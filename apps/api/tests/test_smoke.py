from collections.abc import Callable

import httpx

from ddq_api.ops.smoke import CheckResult, run_smoke

API = "https://api.example.com"
WEB = "https://app.example.com"

API_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
    "x-request-id": "abc12345",
}
WEB_HEADERS = {
    "content-security-policy": "default-src 'self'",
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "strict-transport-security": "max-age=63072000",
}


def _handler(
    *, db_ok: bool = True, cors_for_evil: bool = False, web_root: bool = True
) -> Callable[[httpx.Request], httpx.Response]:
    def handle(request: httpx.Request) -> httpx.Response:
        origin = request.headers.get("origin")
        if request.url.host == "app.example.com":
            body = '<div id="root"></div>' if web_root else "<html></html>"
            return httpx.Response(200, text=body, headers=WEB_HEADERS)
        headers = dict(API_HEADERS)
        if origin == WEB or (origin == "https://evil.example" and cors_for_evil):
            headers["access-control-allow-origin"] = origin
        if request.url.path == "/health":
            data = {"status": "ok", "version": "0.1.0", "environment": "production"}
            return httpx.Response(
                200, json={"data": data, "error": None, "meta": {}}, headers=headers
            )
        data = {"status": "ready" if db_ok else "degraded", "checks": {"database": {"ok": db_ok}}}
        return httpx.Response(
            200 if db_ok else 503,
            json={"data": data, "error": None, "meta": {}},
            headers=headers,
        )

    return handle


def _run(**kwargs: bool) -> list[CheckResult]:
    client = httpx.Client(transport=httpx.MockTransport(_handler(**kwargs)))
    return run_smoke(API, WEB, client)


def test_all_checks_pass_on_a_healthy_deployment() -> None:
    results = _run()
    assert results
    assert all(r.ok for r in results), [r for r in results if not r.ok]


def test_fails_when_database_is_down() -> None:
    failed = {r.name for r in _run(db_ok=False) if not r.ok}
    assert "api /ready database" in failed


def test_fails_when_cors_allows_an_unknown_origin() -> None:
    failed = {r.name for r in _run(cors_for_evil=True) if not r.ok}
    assert "api CORS rejects unknown origin" in failed


def test_fails_when_web_shell_is_missing() -> None:
    failed = {r.name for r in _run(web_root=False) if not r.ok}
    assert "web serves the app shell" in failed


def test_trailing_slashes_are_tolerated() -> None:
    client = httpx.Client(transport=httpx.MockTransport(_handler()))
    assert all(r.ok for r in run_smoke(API + "/", WEB + "/", client))


def test_network_errors_are_reported_as_a_failed_check_not_a_traceback() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = httpx.Client(transport=httpx.MockTransport(refuse))
    results = run_smoke(API, WEB, client)
    assert [r.ok for r in results] == [False]
    assert results[0].name == "reachability"
    assert "ConnectError" in results[0].detail
