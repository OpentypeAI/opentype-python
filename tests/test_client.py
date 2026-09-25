from __future__ import annotations

import httpx
import pydantic
import pytest
import respx

import opentype
from opentype import AsyncOpenType, OpenType, OpenTypeError

from .conftest import BASE, run_json


def test_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENTYPE_API_KEY", raising=False)
    with pytest.raises(OpenTypeError) as exc:
        OpenType()
    assert exc.value.code == "missing_credentials"


def test_env_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENTYPE_API_KEY", "otsk_env")
    monkeypatch.setenv("OPENTYPE_BASE_URL", "https://env.test/")
    c = OpenType()
    assert c.api_key == "otsk_env"
    assert str(c.base_url) == "https://env.test/"


def test_default_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENTYPE_BASE_URL", raising=False)
    assert str(OpenType(api_key="k").base_url) == "https://api.opentype.dev/"
    assert opentype.DEFAULT_BASE_URL == "https://api.opentype.dev"


@respx.mock
def test_auth_header_and_request_id(client: OpenType) -> None:
    route = respx.get(f"{BASE}/v1/runs/run_1").mock(
        return_value=httpx.Response(200, json=run_json(), headers={"x-request-id": "req_9"})
    )
    run = client.runs.get("run_1")
    req = route.calls.last.request
    assert req.headers["authorization"] == "Bearer otsk_test"
    assert req.headers["user-agent"].startswith("opentype-python/")
    assert run.run_id == "run_1" and run.state == "completed"
    assert run._request_id == "req_9"


@respx.mock
def test_custom_http_client_and_base_path() -> None:
    route = respx.get("https://proxy.test/prefix/v1/quota").mock(return_value=httpx.Response(200, json={}))
    http = httpx.Client(headers={"x-extra": "1"})
    c = OpenType(api_key="k", base_url="https://proxy.test/prefix", http_client=http)
    with pytest.raises(pydantic.ValidationError):
        c.usage.quota()  # empty body does not validate
    assert route.called
    assert route.calls.last.request.headers["x-extra"] == "1"
    c.close()
    assert not http.is_closed  # caller owns it


@respx.mock
def test_unknown_fields_kept(client: OpenType) -> None:
    respx.get(f"{BASE}/v1/runs/run_1").mock(return_value=httpx.Response(200, json=run_json(new_field=1)))
    run = client.runs.get("run_1")
    assert run.model_extra == {"new_field": 1}


@respx.mock
async def test_async_basic(aclient: AsyncOpenType) -> None:
    route = respx.get(f"{BASE}/v1/runs/run_1").mock(return_value=httpx.Response(200, json=run_json()))
    run = await aclient.runs.get("run_1")
    assert run.run_id == "run_1"
    assert route.calls.last.request.headers["authorization"] == "Bearer otsk_test"
