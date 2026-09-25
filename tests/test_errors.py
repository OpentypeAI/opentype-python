from __future__ import annotations

import httpx
import pytest
import respx

import opentype
from opentype import (
    APIStatusError,
    AuthenticationError,
    ConflictError,
    InsufficientCreditsError,
    InvalidRequestError,
    NotFoundError,
    OpenType,
    OpenTypeError,
    PermissionDeniedError,
    RateLimitError,
    ServerError,
)

from .conftest import BASE, err

CASES = [
    (400, "invalid_body", InvalidRequestError),
    (400, "unknown_model", InvalidRequestError),
    (401, "missing_credentials", AuthenticationError),
    (401, "invalid_credential", AuthenticationError),
    (402, "insufficient_credits", InsufficientCreditsError),
    (403, "scope_denied", PermissionDeniedError),
    (404, "run_not_found", NotFoundError),
    (409, "idempotency_conflict", ConflictError),
    (413, "payload_too_large", InvalidRequestError),
    (429, "quota_exceeded", RateLimitError),
    (500, "internal", ServerError),
    (503, "verdict_schema_violation", ServerError),
    (504, "deadline_exceeded", ServerError),
    (418, "teapot", APIStatusError),
]


@pytest.mark.parametrize(("status", "code", "cls"), CASES)
@respx.mock
def test_error_mapping(status: int, code: str, cls: type[Exception]) -> None:
    respx.get(f"{BASE}/v1/runs/r").mock(return_value=httpx.Response(status, json=err(code, "msg")))
    client = OpenType(api_key="k", base_url=BASE, max_retries=0)
    with pytest.raises(cls) as exc:
        client.runs.get("r")
    e = exc.value
    assert isinstance(e, OpenTypeError)
    assert (e.status, e.code, e.message, e.request_id) == (status, code, "msg", "req_1")
    assert e.violations is None
    assert code in str(e)


@respx.mock
def test_plain_text_body_and_header_request_id(client: OpenType) -> None:
    respx.get(f"{BASE}/v1/runs/r").mock(
        return_value=httpx.Response(413, text="length limit exceeded", headers={"x-request-id": "hdr"})
    )
    with pytest.raises(InvalidRequestError) as exc:
        client.runs.get("r")
    assert exc.value.code == "http_413"
    assert exc.value.message == "length limit exceeded"
    assert exc.value.request_id == "hdr"


@respx.mock
def test_violations(client: OpenType) -> None:
    respx.post(f"{BASE}/v1/runs").mock(
        return_value=httpx.Response(503, json=err("verdict_schema_violation", violations=["/a", "/b"]))
    )
    with pytest.raises(ServerError) as exc:
        client.runs.create({"schema": {}, "messages": [], "max_output_tokens": 1})
    assert exc.value.violations == ["/a", "/b"]


def test_hierarchy_and_aliases() -> None:
    for cls in (AuthenticationError, PermissionDeniedError, InsufficientCreditsError, RateLimitError, ServerError):
        assert issubclass(cls, APIStatusError) and issubclass(cls, OpenTypeError)
    assert issubclass(opentype.APITimeoutError, opentype.APIConnectionError)
    assert opentype.BadRequestError is InvalidRequestError
    assert opentype.QuotaExceededError is RateLimitError
    assert opentype.InternalServerError is ServerError
