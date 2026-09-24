import pytest
from pydantic import ValidationError

from ddq_api.core.envelope import Envelope, ErrorBody, fail, ok


def test_ok_wraps_data_with_empty_error_and_meta() -> None:
    assert ok({"a": 1}).model_dump(mode="json") == {"data": {"a": 1}, "error": None, "meta": {}}


def test_ok_copies_meta() -> None:
    meta = {"page": 1}
    envelope = ok([1], meta=meta)
    meta["page"] = 99
    assert envelope.meta == {"page": 1}


def test_fail_builds_error_body() -> None:
    body = fail("not_found", "nope", {"id": 3}).model_dump(mode="json")
    assert body == {
        "data": None,
        "error": {"code": "not_found", "message": "nope", "details": {"id": 3}},
        "meta": {},
    }


def test_envelope_is_frozen() -> None:
    envelope = ok(1)
    with pytest.raises(ValidationError):
        envelope.data = 2  # type: ignore[misc]


def test_error_body_is_frozen() -> None:
    with pytest.raises(ValidationError):
        ErrorBody(code="x", message="y").code = "z"  # type: ignore[misc]


def test_envelope_generic_parametrisation() -> None:
    assert Envelope[int](data=1).data == 1
