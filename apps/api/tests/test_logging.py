import io
import json
import logging

from ddq_api.core.logging import (
    JsonFormatter,
    configure_logging,
    request_id_var,
)


def _logger(stream: io.StringIO) -> logging.Logger:
    logger = logging.getLogger("test.json")
    logger.handlers.clear()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def test_emits_one_json_object_with_request_id_and_context() -> None:
    stream = io.StringIO()
    token = request_id_var.set("req-12345678")
    try:
        _logger(stream).info("hello", extra={"ctx": {"path": "/x"}})
    finally:
        request_id_var.reset(token)
    payload = json.loads(stream.getvalue())
    assert payload["msg"] == "hello"
    assert payload["level"] == "INFO"
    assert payload["request_id"] == "req-12345678"
    assert payload["path"] == "/x"


def test_request_id_defaults_to_dash() -> None:
    stream = io.StringIO()
    _logger(stream).info("hello")
    assert json.loads(stream.getvalue())["request_id"] == "-"


def test_context_cannot_overwrite_core_fields() -> None:
    stream = io.StringIO()
    _logger(stream).info("real", extra={"ctx": {"msg": "forged", "level": "FATAL"}})
    payload = json.loads(stream.getvalue())
    assert payload["msg"] == "real"
    assert payload["level"] == "INFO"


def test_includes_exception_text() -> None:
    stream = io.StringIO()
    logger = _logger(stream)
    try:
        raise ValueError("boom")
    except ValueError:
        logger.exception("failed")
    assert "ValueError: boom" in json.loads(stream.getvalue())["exc"]


def test_configure_logging_is_idempotent() -> None:
    configure_logging()
    configure_logging()
    flagged = [h for h in logging.getLogger().handlers if getattr(h, "_ddq_json_handler", False)]
    assert len(flagged) == 1
