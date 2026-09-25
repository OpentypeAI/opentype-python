from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

from opentype import AsyncOpenType, BadRequestError, OpenType, RunPendingError
from opentype.types import RouterModelFilters, RouterWeights

from .conftest import BASE, err, run_json

WINDOW = {"start_at": "2026-09-01T00:00:00Z", "end_at": "2026-09-24T00:00:00Z"}
TOTALS = {"input_tokens": 1, "output_tokens": 2, "total_tokens": 3}
SPEND = {"reserved_micros": 0, "settled_micros": 5, "unsettled_micros": 0}


def body(route: respx.Route) -> Any:
    return json.loads(route.calls.last.request.content)


@respx.mock
def test_decide_body_and_key(client: OpenType) -> None:
    route = respx.post(f"{BASE}/v1/runs").mock(
        return_value=httpx.Response(
            200,
            json=run_json(
                decision={
                    "answers": {"urgent": {"type": "noul", "probability": 0.9}},
                    "draws": 1,
                    "read": "slot_constrained",
                }
            ),
        )
    )
    run = client.decide(state={"x": 1}, questions={"urgent": {"type": "noul", "instructions": "?"}}, draws=2)
    sent = body(route)
    assert sent == {
        "kind": "decision",
        "state": {"x": 1},
        "questions": {"urgent": {"type": "noul", "instructions": "?"}},
        "draws": 2,
        "max_output_tokens": 64,
    }
    assert len(route.calls.last.request.headers["idempotency-key"]) == 36
    assert run.decision is not None and run.decision.answers["urgent"]["probability"] == 0.9


@respx.mock
def test_verdict_uses_caller_key(client: OpenType) -> None:
    route = respx.post(f"{BASE}/v1/runs").mock(
        return_value=httpx.Response(200, json=run_json(kind="verdict", verdict={"ok": True}))
    )
    run = client.verdict(
        messages=[{"role": "user", "content": "hi"}],
        schema={"type": "object"},
        max_output_tokens=16,
        idempotency_key="k1",
    )
    assert route.calls.last.request.headers["idempotency-key"] == "k1"
    assert body(route) == {
        "kind": "verdict",
        "messages": [{"role": "user", "content": "hi"}],
        "schema": {"type": "object"},
        "max_output_tokens": 16,
    }
    assert run.verdict == {"ok": True}


@respx.mock
def test_pending_replay_surfaces(client: OpenType) -> None:
    respx.post(f"{BASE}/v1/runs").mock(return_value=httpx.Response(202, json=run_json(state="running", replayed=True)))
    with pytest.raises(RunPendingError) as exc:
        client.runs.create(
            {"kind": "decision", "state": {}, "questions": {}, "max_output_tokens": 1}, idempotency_key="k"
        )
    assert exc.value.status == 202
    assert exc.value.run.state == "running"
    assert respx.calls.call_count == 1


@respx.mock
async def test_async_pending_replay(aclient: AsyncOpenType) -> None:
    respx.post(f"{BASE}/v1/runs").mock(return_value=httpx.Response(202, json=run_json(state="pending", replayed=True)))
    with pytest.raises(RunPendingError):
        await aclient.decide(state="s", questions={})


@respx.mock
def test_usage_endpoints(client: OpenType) -> None:
    summary = respx.get(f"{BASE}/v1/usage").mock(
        return_value=httpx.Response(
            200,
            json={
                "organization_id": "org",
                "window": WINDOW,
                "runs": {"total": 1, "completed": 1, "failed": 0, "in_flight": 0},
                "tokens": TOTALS,
                "spend": SPEND,
            },
        )
    )
    s = client.usage.summary(**WINDOW)
    assert s.organization_id == "org"
    assert dict(summary.calls.last.request.url.params) == WINDOW
    ledger = respx.get(f"{BASE}/v1/usage/ledger").mock(
        return_value=httpx.Response(200, json={"organization_id": "o", "window": WINDOW, "limit": 5, "entries": []})
    )
    client.usage.ledger(limit=5)
    assert dict(ledger.calls.last.request.url.params) == {"limit": "5"}
    respx.get(f"{BASE}/v1/usage/daily").mock(
        return_value=httpx.Response(200, json={"organization_id": "o", "window": WINDOW, "days": []})
    )
    assert client.usage.daily().days == []


@respx.mock
def test_keys(client: OpenType) -> None:
    key = {
        "id": "key_1",
        "name": "ci",
        "principal": {"type": "user", "id": "u"},
        "scopes": ["runs_read"],
        "state": "active",
        "secret_prefix": "otsk_ab",
        "created_by": "u",
        "created_at": "2026-09-24T00:00:00Z",
    }
    respx.get(f"{BASE}/v1/keys").mock(return_value=httpx.Response(200, json={"keys": [key]}))
    respx.get(f"{BASE}/v1/keys/key_1").mock(return_value=httpx.Response(200, json=key))
    revoke = respx.delete(f"{BASE}/v1/keys/key_1").mock(
        return_value=httpx.Response(200, json={**key, "state": "revoked"})
    )
    respx.post(f"{BASE}/v1/keys/key_1/rotate").mock(
        return_value=httpx.Response(200, json={**key, "secret": "otsk_new"})
    )
    assert client.keys.list().keys[0].id == "key_1"
    assert client.keys.get("key_1").name == "ci"
    assert client.keys.revoke("key_1").state == "revoked"
    assert revoke.called
    assert client.keys.rotate("key_1").secret == "otsk_new"


@respx.mock
def test_billing(client: OpenType) -> None:
    b = {
        "organization_id": "o",
        "balance_micros": 1,
        "currency": "usd",
        "auto_recharge": {"enabled": False},
        "has_payment_method": False,
        "transactions": [],
    }
    respx.get(f"{BASE}/v1/billing").mock(return_value=httpx.Response(200, json=b))
    put = respx.put(f"{BASE}/v1/billing/auto-recharge").mock(return_value=httpx.Response(200, json=b))
    respx.post(f"{BASE}/v1/billing/checkout").mock(
        return_value=httpx.Response(200, json={"checkout_url": "https://pay"})
    )
    respx.post(f"{BASE}/v1/billing/portal").mock(
        return_value=httpx.Response(200, json={"portal_url": "https://portal"})
    )
    assert client.billing.get().balance_micros == 1
    client.billing.set_auto_recharge(enabled=True, threshold_micros=1, amount_micros=5_000_000)
    assert body(put) == {"enabled": True, "threshold_micros": 1, "amount_micros": 5_000_000}
    assert client.billing.checkout(amount_micros=5_000_000).checkout_url == "https://pay"
    assert client.billing.portal().portal_url == "https://portal"


def _contribution(benchmark: str, **extra: Any) -> dict[str, Any]:
    return {
        "benchmark": benchmark,
        "name": benchmark.upper(),
        "value": 70.0,
        "rank": 2,
        "norm": 0.8,
        "weight": 0.5,
        "contribution": 0.4,
        **extra,
    }


def _entry(model_id: str, provider: str, cost: float) -> dict[str, Any]:
    return {
        "id": model_id,
        "name": model_id.upper(),
        "provider": provider,
        "open_weights": True,
        "score": 0.9,
        "blended_price_per_mtok": 1.0,
        "domain_score": 0.82,
        "expected_quality": 0.82,
        "uncertainty": 0.1,
        "estimated_cost_usd": cost,
        "estimated_latency_ms": 2300.0,
        "latency_estimated": False,
        "strengths": [_contribution("swe_bench_verified")],
        "weaknesses": [_contribution("aime", gap_to_best=-0.05)],
        "imputed": [{"benchmark": "aime", "rule": "correlated", "from": "gpqa"}],
    }


def _label(label: str) -> dict[str, Any]:
    return {"label": label, "probabilities": {label: 0.8}}


SELECT = {
    "id": "rtr_1",
    "run_id": "run_1",
    "policy": "balanced",
    "model": {"id": "m1", "name": "M1", "provider": "p", "open_weights": True},
    "classification": {
        "domain": _label("coding"),
        "difficulty": _label("hard"),
        "task_type": {
            "label": "code_generation",
            "family": "coding",
            "top": [{"task_type": "code_generation", "family": "coding", "probability": 0.7}],
            "fixed": False,
        },
        "facets": {
            "difficulty_expected": 1.8,
            "difficulty": _label("hard"),
            "output_length": _label("medium"),
            "output_tokens_est": 800.0,
            "needs_tools": 0.1,
            "needs_vision": 0.0,
            "safety_sensitive": 0.0,
            "language": "en",
            "input_tokens_est": 12,
        },
    },
    "ranking": [_entry("m1", "p", 0.0021), _entry("m2", "q", 0.0150)],
    "score_basis": "benchmarks",
    "threshold": {"q_star": 0.9, "r": 0.85, "tau": 0.765},
    "filters_applied": [{"filter": "open_weights", "removed": 3}],
    "low_confidence": False,
    "input_tokens_est": 12,
    "reason": "cheapest above the floor",
    "decision_model": "neon-1.1",
    "catalog_as_of": "2026-09-24",
    "benchmarks_as_of": "2026-09-20",
    "cost_micros": 10,
    "replayed": False,
}


def _model(model_id: str, provider: str, open_weights: bool, domains: list[str]) -> dict[str, Any]:
    return {
        "id": model_id,
        "name": model_id.upper(),
        "provider": provider,
        "open_weights": open_weights,
        "context_tokens": 262144,
        "modalities": ["text"],
        "price_input_per_mtok": 0.5,
        "price_output_per_mtok": 2.0,
        "blended_price_per_mtok": 0.875,
        "reasoning_token_factor": 1.0,
        "scores": {"intelligence": 60, "coding": 80},
        "domains": domains,
        "highlights": [],
        "benchmarks_measured": 12,
    }


CATALOG = {
    "as_of": "2026-09-24",
    "benchmarks_as_of": "2026-09-20",
    "source": "test",
    "domains": ["coding"],
    "task_types": ["code_generation"],
    "policies": ["balanced"],
    "models": [_model("m1", "p", True, ["coding"]), _model("m2", "q", False, [])],
}
TASK_TYPES = {
    "benchmarks_as_of": "2026-09-20",
    "families": ["coding"],
    "task_types": [
        {
            "id": "code_generation",
            "family": "coding",
            "domain": "coding",
            "description": "Write new code.",
            "turns": 1.0,
            "weights": [{"benchmark": "swe_bench_verified", "name": "SWE-bench Verified", "weight": 0.6}],
        }
    ],
}


@respx.mock
def test_router(client: OpenType) -> None:
    sel = respx.post(f"{BASE}/v1/router/select").mock(return_value=httpx.Response(200, json=SELECT))
    respx.get(f"{BASE}/v1/router/models").mock(return_value=httpx.Response(200, json=CATALOG))
    r = client.route("fix this bug", policy="cost_efficient", models={"open_weights": True, "exclude": None})
    assert r.model.id == "m1" and r.classification.domain.label == "coding"
    assert r.classification.task_type.label == "code_generation" and not r.classification.task_type.fixed
    assert r.classification.facets.output_length.label == "medium"
    top = r.ranking[0]
    assert top.estimated_cost_usd == 0.0021 and top.strengths[0].benchmark == "swe_bench_verified"
    assert top.weaknesses[0].gap_to_best == -0.05 and top.imputed[0].from_ == "gpqa"
    assert r.threshold is not None and r.threshold.tau == 0.765 and r.run_id == "run_1"
    assert body(sel) == {"prompt": "fix this bug", "policy": "cost_efficient", "models": {"open_weights": True}}
    assert "idempotency-key" not in sel.calls.last.request.headers
    assert [m.id for m in client.router.models().models] == ["m1", "m2"]
    with pytest.raises(ValueError):
        client.router.select()
    with pytest.raises(ValueError):
        client.router.select(prompt="a", messages=[{"role": "user", "content": "b"}])


@respx.mock
def test_router_v2_knobs_and_task_types(client: OpenType) -> None:
    sel = respx.post(f"{BASE}/v1/router/select").mock(return_value=httpx.Response(200, json=SELECT))
    respx.get(f"{BASE}/v1/router/task-types").mock(return_value=httpx.Response(200, json=TASK_TYPES))
    client.router.select(
        prompt="x",
        task_type="code_generation",
        latency="interactive",
        max_latency_ms=5000.0,
        weights=RouterWeights(quality=0.6, cost=0.4),
        models=RouterModelFilters(providers=["openai"]),
    )
    assert body(sel) == {
        "prompt": "x",
        "task_type": "code_generation",
        "latency": "interactive",
        "max_latency_ms": 5000.0,
        "weights": {"quality": 0.6, "cost": 0.4},
        "models": {"providers": ["openai"]},
    }
    client.route("y", weights={"speed": 1.0, "cost": None})
    assert body(sel) == {"prompt": "y", "weights": {"speed": 1.0}}
    tt = client.router.task_types()
    assert tt.task_types[0].id == "code_generation" and tt.task_types[0].weights[0].weight == 0.6


@respx.mock
def test_router_weights_require_balanced(client: OpenType) -> None:
    respx.post(f"{BASE}/v1/router/select").mock(return_value=httpx.Response(400, json=err("weights_require_balanced")))
    with pytest.raises(BadRequestError) as exc:
        client.router.select(prompt="x", policy="cost_efficient", weights={"quality": 1.0})
    assert exc.value.code == "weights_require_balanced"


@respx.mock
async def test_async_router_and_usage(aclient: AsyncOpenType) -> None:
    respx.post(f"{BASE}/v1/router/select").mock(return_value=httpx.Response(200, json=SELECT))
    respx.get(f"{BASE}/v1/router/models").mock(return_value=httpx.Response(200, json=CATALOG))
    respx.get(f"{BASE}/v1/router/task-types").mock(return_value=httpx.Response(200, json=TASK_TYPES))
    assert (await aclient.route(messages=[{"role": "user", "content": "x"}], latency="batch")).model.id == "m1"
    assert len((await aclient.router.models()).models) == 2
    assert (await aclient.router.task_types()).families == ["coding"]
    respx.get(f"{BASE}/v1/keys").mock(return_value=httpx.Response(200, json={"keys": []}))
    assert (await aclient.keys.list()).keys == []
