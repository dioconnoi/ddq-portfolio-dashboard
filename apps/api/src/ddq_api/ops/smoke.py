"""Post-deploy smoke checks: python -m ddq_api.ops.smoke --api URL --web URL"""

import argparse
import sys
from dataclasses import dataclass
from typing import Any

import httpx

_REQUEST_TIMEOUT_S = 120.0  # the free-tier API may be asleep
_EVIL_ORIGIN = "https://evil.example"
_API_HEADERS = ("x-content-type-options", "x-frame-options", "referrer-policy", "x-request-id")
_WEB_HEADERS = (
    "content-security-policy",
    "x-content-type-options",
    "x-frame-options",
    "strict-transport-security",
)


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str = ""


def _json(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


def _missing(response: httpx.Response, required: tuple[str, ...]) -> list[str]:
    return [header for header in required if header not in response.headers]


def run_smoke(api_url: str, web_url: str, client: httpx.Client) -> list[CheckResult]:
    api, web = api_url.rstrip("/"), web_url.rstrip("/")
    timeout = _REQUEST_TIMEOUT_S
    health = client.get(f"{api}/health", timeout=timeout)
    ready = client.get(f"{api}/ready", timeout=timeout)
    cors_ok = client.get(f"{api}/health", headers={"Origin": web}, timeout=timeout)
    cors_bad = client.get(f"{api}/health", headers={"Origin": _EVIL_ORIGIN}, timeout=timeout)
    shell = client.get(web, timeout=timeout)

    health_data = _json(health).get("data") or {}
    ready_data = _json(ready).get("data") or {}
    db_ok = ((ready_data.get("checks") or {}).get("database") or {}).get("ok") is True
    api_missing = _missing(health, _API_HEADERS)
    web_missing = _missing(shell, _WEB_HEADERS)

    return [
        CheckResult(
            "api /health",
            health.status_code == 200 and health_data.get("status") == "ok",
            f"status={health.status_code}",
        ),
        CheckResult(
            "api /ready database",
            ready.status_code == 200 and db_ok,
            f"status={ready.status_code}",
        ),
        CheckResult(
            "api CORS allows the web origin",
            cors_ok.headers.get("access-control-allow-origin") == web,
        ),
        CheckResult(
            "api CORS rejects unknown origin",
            "access-control-allow-origin" not in cors_bad.headers,
        ),
        CheckResult("api security headers", not api_missing, f"missing={api_missing}"),
        CheckResult(
            "web serves the app shell",
            shell.status_code == 200 and 'id="root"' in shell.text,
            f"status={shell.status_code}",
        ),
        CheckResult("web security headers", not web_missing, f"missing={web_missing}"),
    ]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Post-deploy smoke checks")
    parser.add_argument("--api", required=True, help="API base URL")
    parser.add_argument("--web", required=True, help="Web app base URL")
    args = parser.parse_args(argv)
    with httpx.Client(follow_redirects=True) as client:
        results = run_smoke(args.api, args.web, client)
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        sys.stdout.write(f"{status}  {result.name}  {result.detail}\n")
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
