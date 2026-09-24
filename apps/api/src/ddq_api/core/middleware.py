"""HTTP middleware: request context, headers, body limit, rate limiting, error catch-all."""

import ipaddress
import logging
import math
import re
import time
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from limits import parse as parse_rate_limit
from limits.aio.storage import MemoryStorage
from limits.aio.strategies import FixedWindowRateLimiter
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ddq_api.core.config import Settings
from ddq_api.core.envelope import fail
from ddq_api.core.logging import request_id_var

_access_log = logging.getLogger("ddq_api.access")
_error_log = logging.getLogger("ddq_api.errors")
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
_IPV6_PREFIX = 64


def _normalise_ip(candidate: str) -> str | None:
    """A valid address as a rate-limit key; IPv6 collapses to its /64 (one subscriber's block)."""
    try:
        address = ipaddress.ip_address(candidate)
    except ValueError:
        return None
    if isinstance(address, ipaddress.IPv6Address):
        if address.ipv4_mapped is not None:
            return str(address.ipv4_mapped)
        return str(ipaddress.ip_network(f"{address}/{_IPV6_PREFIX}", strict=False))
    return str(address)


def client_ip(request: Request, hops: int) -> str:
    """Resolve the client address used as the rate-limit key.

    Only the entry appended by our own trusted proxy is believed: with ``hops`` trusted
    proxies, that is the ``hops``-th entry from the RIGHT of X-Forwarded-For (all header
    lines joined, since a client can send several). Anything to its left was supplied by the
    client and can be forged. An entry that is not an IP address is never used as a key.
    """
    if hops > 0:
        forwarded = ",".join(request.headers.getlist("x-forwarded-for"))
        entries = [part.strip() for part in forwarded.split(",") if part.strip()]
        if len(entries) >= hops:
            normalised = _normalise_ip(entries[-hops])
            if normalised is not None:
                return normalised
    host = request.client.host if request.client else "unknown"
    return _normalise_ip(host) or host


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get("x-request-id", "")
        request_id = incoming if _REQUEST_ID_RE.fullmatch(incoming) else uuid.uuid4().hex
        request.state.request_id = request_id
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
            _access_log.info(
                "request",
                extra={
                    "ctx": {
                        "method": request.method,
                        "path": request.url.path,  # never the query string (may hold tokens)
                        "status": response.status_code,
                        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    }
                },
            )
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_var.reset(token)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, hsts: bool) -> None:
        super().__init__(app)
        self._hsts = hsts

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cache-Control", "no-store")
        if self._hsts:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=63072000; includeSubDomains"
            )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window limiter, in memory: per API instance, which is fine on one free instance."""

    def __init__(self, app: ASGIApp, rate: str, hops: int) -> None:
        super().__init__(app)
        self._item = parse_rate_limit(rate)
        self._limiter = FixedWindowRateLimiter(MemoryStorage())
        self._hops = hops

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        key = client_ip(request, self._hops)
        if await self._limiter.hit(self._item, key):
            return await call_next(request)
        stats = await self._limiter.get_window_stats(self._item, key)
        retry_after = max(1, math.ceil(stats.reset_time - time.time()))
        envelope = fail("rate_limited", "Too many requests; please slow down")
        return JSONResponse(
            status_code=429,
            content=envelope.model_dump(mode="json"),
            headers={"Retry-After": str(retry_after)},
        )


class BodySizeLimitMiddleware:
    """Rejects oversized bodies by Content-Length, and unsized (chunked) bodies outright.

    Phase 3 (CSV upload) replaces this with streaming byte counting.
    """

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self._max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        rejection = self._rejection(scope)
        if rejection is not None:
            await rejection(scope, receive, send)
            return
        await self.app(scope, receive, send)

    def _rejection(self, scope: Scope) -> JSONResponse | None:
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        length = headers.get("content-length")
        chunked = "chunked" in headers.get("transfer-encoding", "").lower()
        if length is not None and chunked:
            # Ambiguous framing is the classic request-smuggling shape; never accept it.
            return _error(400, "bad_request", "Conflicting Content-Length and Transfer-Encoding")
        if length is not None:
            if not (length.isascii() and length.isdigit()) or int(length) > self._max_bytes:
                return _error(413, "payload_too_large", "Request body is too large")
            return None
        if chunked:
            return _error(411, "length_required", "Content-Length is required")
        return None


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content=fail(code, message).model_dump(mode="json"))


class UnhandledErrorMiddleware:
    """Innermost layer: turns an unexpected exception into the 500 envelope.

    Doing it here (instead of in Starlette's outermost error handler) keeps the response inside
    the request-context, security-header and CORS layers, so browsers can read it and the
    failure reaches the access log.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = False

        async def tracking_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, tracking_send)
        except Exception as error:
            if started:
                raise  # too late to change the response; let the server close the connection
            _error_log.error(
                "unhandled exception", exc_info=error, extra={"ctx": {"path": scope["path"]}}
            )
            response = _error(500, "internal_error", "An unexpected error occurred")
            await response(scope, receive, send)


def install_middleware(app: FastAPI, settings: Settings) -> None:
    """Add innermost first: Starlette makes the LAST added the outermost layer."""
    app.add_middleware(UnhandledErrorMiddleware)
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_bytes)
    app.add_middleware(
        RateLimitMiddleware,
        rate=settings.rate_limit_default,
        hops=settings.trusted_proxy_hops,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=False,  # bearer tokens travel in the Authorization header, not cookies
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Retry-After"],
        max_age=600,
    )
    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.environment == "production")
    app.add_middleware(RequestContextMiddleware)
