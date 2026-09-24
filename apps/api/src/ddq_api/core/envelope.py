"""The single response envelope used by every endpoint."""

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorBody(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    message: str
    details: dict[str, Any] | None = None


class Envelope[T](BaseModel):
    model_config = ConfigDict(frozen=True)

    data: T | None = None
    error: ErrorBody | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


def ok[T](data: T, meta: Mapping[str, Any] | None = None) -> Envelope[T]:
    return Envelope(data=data, meta=dict(meta or {}))


def fail(code: str, message: str, details: dict[str, Any] | None = None) -> Envelope[None]:
    return Envelope(error=ErrorBody(code=code, message=message, details=details))
