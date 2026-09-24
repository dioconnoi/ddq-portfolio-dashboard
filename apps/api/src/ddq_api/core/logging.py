"""Structured JSON logging with a per-request correlation id."""

import contextvars
import json
import logging
import sys
from typing import Any

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

_HANDLER_FLAG = "_ddq_json_handler"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        context = getattr(record, "ctx", None)
        core: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        if record.exc_info:
            core["exc"] = self.formatException(record.exc_info)
        extra = context if isinstance(context, dict) else {}
        # Core fields win so callers cannot forge them (log-injection hardening).
        return json.dumps({**extra, **core}, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Install a single stdout JSON handler; safe to call repeatedly."""
    root = logging.getLogger()
    for handler in [h for h in root.handlers if getattr(h, _HANDLER_FLAG, False)]:
        root.removeHandler(handler)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    setattr(handler, _HANDLER_FLAG, True)
    root.addHandler(handler)
    root.setLevel(level)
