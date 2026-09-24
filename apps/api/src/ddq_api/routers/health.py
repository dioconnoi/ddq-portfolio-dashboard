"""Liveness (/health) and readiness (/ready). Liveness must never touch dependencies."""

import asyncio
import logging
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ddq_api import __version__
from ddq_api.core.config import Settings
from ddq_api.core.envelope import Envelope, ErrorBody, ok

logger = logging.getLogger("ddq_api.health")
router = APIRouter(tags=["health"])

_DB_TIMEOUT_S = 3.0


class HealthOut(BaseModel):
    status: Literal["ok"]
    version: str
    environment: str


class CheckOut(BaseModel):
    ok: bool


class ReadyOut(BaseModel):
    status: Literal["ready", "degraded"]
    checks: dict[str, CheckOut]


@router.get("/health", response_model=Envelope[HealthOut])
async def health(request: Request) -> Envelope[HealthOut]:
    settings: Settings = request.app.state.settings
    return ok(HealthOut(status="ok", version=__version__, environment=settings.environment))


@router.get(
    "/ready",
    response_model=Envelope[ReadyOut],
    responses={503: {"model": Envelope[ReadyOut]}},
)
async def ready(request: Request) -> Envelope[ReadyOut] | JSONResponse:
    db_health = getattr(request.app.state, "db_health", None)
    db_ok = False
    if db_health is not None:
        try:
            await asyncio.wait_for(db_health.ping(), timeout=_DB_TIMEOUT_S)
            db_ok = True
        except Exception:  # any failure means "not ready"; detail is logged, never returned
            logger.warning("database readiness check failed", exc_info=True)

    body = ReadyOut(
        status="ready" if db_ok else "degraded", checks={"database": CheckOut(ok=db_ok)}
    )
    if db_ok:
        return ok(body)
    envelope = Envelope[ReadyOut](
        data=body,
        error=ErrorBody(code="not_ready", message="One or more dependencies are unavailable"),
    )
    return JSONResponse(status_code=503, content=envelope.model_dump(mode="json"))
