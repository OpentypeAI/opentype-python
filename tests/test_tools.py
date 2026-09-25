from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

from opentype import OpenType
from opentype.tools import TOOLS, anthropic_tools, openai_tools

from .conftest import BASE, err, run_json
from .test_resources import CATALOG, SELECT

NAMES = [
    "opentype_decide",
    "opentype_verdict",
    "opentype_route_model",
    "opentype_list_models",
    "opentype_get_run",
    "opentype_usage",
]


def test_six_tools_same_names() -> None:
    assert [t.name for t in TOOLS] == NAMES


def test_openai_shape(client: OpenType) -> None:
    tools = openai_tools(client)
    for d in tools.definitions:
        assert d["type"] == "function"
        assert set(d["function"]) == {"name", "description", "parameters"}
        assert d["function"]["parameters"]["type"] == "object"
    assert tools.responses_definitions[0]["name"] == "opentype_decide"
    assert tools.responses_definitions[0]["type"] == "function"


def test_anthropic_shape(client: OpenType) -> None:
    for d in anthropic_tools(client).definitions:
        assert set(d) == {"name", "description", "input_schema"}
        assert d["input_schema"]["type"] == "object"


def test_schemas_are_valid_json_schema_objects() -> None:
    for t in TOOLS:
        json.dumps(t.input_schema)
        for req in t.input_schema.get("required", []):
            assert req in t.input_schema["properties"]


@respx.mock
def test_openai_handle_decide(client: OpenType) -> None:
    route = respx.post(f"{BASE}/v1/runs").mock(return_value=httpx.Response(200, json=run_json()))
    tools = openai_tools(client)
    call = {
        "id": "call_1",
        "type": "function",
        "function": {"name": "opentype_decide", "arguments": json.dumps({"state": "s", "questions": {}, "draws": 2})},
    }
    msg = tools.handle_tool_call(call)
    assert msg["role"] == "tool" and msg["tool_call_id"] == "call_1"
    assert json.loads(msg["content"])["run_id"] == "run_1"
    assert json.loads(route.calls.last.request.content)["draws"] == 2


@respx.mock
def test_handle_get_run_and_error(client: OpenType) -> None:
    respx.get(f"{BASE}/v1/runs/run_1").mock(return_value=httpx.Response(200, json=run_json()))
    respx.get(f"{BASE}/v1/runs/nope").mock(return_value=httpx.Response(404, json=err("run_not_found")))
    tools = anthropic_tools(client)
    ok = tools.handle_tool_use(
        {"type": "tool_use", "id": "tu_1", "name": "opentype_get_run", "input": {"run_id": "run_1"}}
    )
    assert ok["type"] == "tool_result" and ok["tool_use_id"] == "tu_1" and "is_error" not in ok
    bad = tools.handle_tool_use(
        {"type": "tool_use", "id": "tu_2", "name": "opentype_get_run", "input": {"run_id": "nope"}}
    )
    assert bad["is_error"] is True
    assert json.loads(bad["content"])["error"]["code"] == "run_not_found"


@respx.mock
def test_verdict_route_models_usage(client: OpenType) -> None:
    respx.post(f"{BASE}/v1/runs").mock(
        return_value=httpx.Response(200, json=run_json(kind="verdict", verdict={"a": 1}))
    )
    respx.post(f"{BASE}/v1/router/select").mock(return_value=httpx.Response(200, json=SELECT))
    respx.get(f"{BASE}/v1/router/models").mock(return_value=httpx.Response(200, json=CATALOG))
    usage = respx.get(f"{BASE}/v1/usage").mock(
        return_value=httpx.Response(
            200,
            json={
                "organization_id": "o",
                "window": {"start_at": "a", "end_at": "b"},
                "runs": {"total": 0, "completed": 0, "failed": 0, "in_flight": 0},
                "tokens": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                "spend": {"reserved_micros": 0, "settled_micros": 0, "unsettled_micros": 0},
            },
        )
    )
    tools = openai_tools(client)
    v = json.loads(
        tools.handle(
            "opentype_verdict", {"messages": [{"role": "user", "content": "x"}], "schema": {}, "max_output_tokens": 8}
        )
    )
    assert v["verdict"] == {"a": 1}
    r = json.loads(tools.handle("opentype_route_model", '{"prompt": "code", "policy": "balanced"}'))
    assert r["model"]["id"] == "m1"
    m = json.loads(tools.handle("opentype_list_models", {"open_weights": True, "domain": "coding"}))
    assert [x["id"] for x in m["models"]] == ["m1"]
    u = json.loads(tools.handle("opentype_usage", {}))
    assert u["usage"]["organization_id"] == "o"
    params = usage.calls.last.request.url.params
    assert params["start_at"].endswith("Z") and params["end_at"].endswith("Z")


@respx.mock
def test_usage_include_quota(client: OpenType) -> None:
    respx.get(f"{BASE}/v1/usage").mock(return_value=httpx.Response(500, json=err("internal")))
    out = json.loads(
        openai_tools(client).handle("opentype_usage", {"start_at": "a", "end_at": "b", "include_quota": True})
    )
    assert out["error"]["code"] == "internal"


def test_unknown_tool(client: OpenType) -> None:
    with pytest.raises(KeyError):
        openai_tools(client).handle("nope", {})


def test_lazy_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENTYPE_API_KEY", "otsk_env")
    t: Any = anthropic_tools()
    assert t.client.api_key == "otsk_env"
