"""Domain errors: raised by services, translated to the envelope by handlers."""

from typing import Any


class DomainError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class ServiceUnavailableError(DomainError):
    status_code = 503
    code = "service_unavailable"
