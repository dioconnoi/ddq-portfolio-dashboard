"""Exception handlers: every failure leaves the API as an envelope, never a stack trace."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ddq_api.core.envelope import Envelope, fail
from ddq_api.core.errors import DomainError
from ddq_api.core.logging import request_id_var

logger = logging.getLogger("ddq_api.errors")

_HTTP_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    413: "payload_too_large",
    429: "rate_limited",
}


def _json(
    status: int, envelope: Envelope[Any], headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status, content=envelope.model_dump(mode="json"), headers=headers
    )


async def _domain_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)  # noqa: S101  (narrowing for mypy)
    return _json(exc.status_code, fail(exc.code, exc.message, exc.details))


async def _validation_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)  # noqa: S101
    errors = [
        {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()
    ]  # input values are deliberately omitted: they may contain secrets
    return _json(422, fail("validation_error", "Request validation failed", {"errors": errors}))


async def _http_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)  # noqa: S101
    code = _HTTP_CODES.get(exc.status_code, "http_error")
    headers = dict(exc.headers) if exc.headers else None
    return _json(exc.status_code, fail(code, str(exc.detail)), headers)


async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "-")
    token = request_id_var.set(request_id)
    try:
        logger.error("unhandled exception", exc_info=exc, extra={"ctx": {"path": request.url.path}})
    finally:
        request_id_var.reset(token)
    return _json(
        500,
        fail("internal_error", "An unexpected error occurred"),
        {"X-Request-ID": request_id},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _domain_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(Exception, _unhandled)
