"""Live tests against a real deployment. Opt-in: OPENTYPE_E2E=1 plus
OPENTYPE_API_KEY (scopes runs_write, runs_read, usage_read). Spends credit.
Runs sequentially on purpose. Router tests skip until the routes are deployed.
The long-context tests send ~20k input tokens each (router + decision)."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest

from opentype import AsyncOpenType, BadRequestError, NotFoundError, OpenType, ServerError
from opentype.types import RunResponse

pytestmark = pytest.mark.skipif(os.environ.get("OPENTYPE_E2E") != "1", reason="set OPENTYPE_E2E=1 to run live tests")

QUESTIONS = {
    "urgent": {"type": "noul", "instructions": "does the customer need a reply within the hour?"},
    "bucket": {
        "type": "choice",
        "instructions": "which queue?",
        "criteria": {"billing": "payment problems", "technical": None},
    },
}


@pytest.fixture(scope="module")
def ot() -> Iterator[OpenType]:
    with OpenType() as c:
        yield c


@pytest.fixture(scope="module")
def decision(ot: OpenType) -> tuple[str, str]:
    key = f"sdk-py-e2e-{uuid.uuid4()}"
    run = ot.decide(state={"ticket": "everything is down, demo at noon"}, questions=QUESTIONS, idempotency_key=key)
    assert run.state == "completed", run
    assert run.decision is not None and set(run.decision.answers) == set(QUESTIONS)
    return run.run_id, key


def test_decide(decision: tuple[str, str]) -> None:
    assert decision[0].startswith("run_")


def test_replay_same_key(ot: OpenType, decision: tuple[str, str]) -> None:
    run_id, key = decision
    run = ot.decide(state={"ticket": "everything is down, demo at noon"}, questions=QUESTIONS, idempotency_key=key)
    assert run.replayed is True and run.run_id == run_id


def test_verdict(ot: OpenType) -> None:
    try:
        run = _verdict(ot)
    except ServerError as e:
        # Neon 1.1 serves decisions only today; a verdict answers 503 no_route_available.
        assert e.code == "no_route_available"
        return
    assert run.state == "completed" and run.verdict is not None
    assert isinstance(run.verdict["complaint"], bool)


def _verdict(ot: OpenType) -> RunResponse:
    return ot.verdict(
        messages=[{"role": "user", "content": "Is 'refund me now or I sue' a complaint? Answer as JSON."}],
        schema={
            "type": "object",
            "properties": {"complaint": {"type": "boolean"}},
            "required": ["complaint"],
            "additionalProperties": False,
        },
        max_output_tokens=64,
    )


def test_get_stream_list(ot: OpenType, decision: tuple[str, str]) -> None:
    run_id = decision[0]
    assert ot.runs.get(run_id).run_id == run_id
    events = list(ot.runs.stream(run_id))
    assert events[0].event == "state" and events[-1].event == "terminal"
    page = ot.runs.list(limit=5)
    assert page.data and all(r.run_id.startswith("run_") for r in page.data)


def test_not_found(ot: OpenType) -> None:
    with pytest.raises(NotFoundError):
        ot.runs.get("run_" + "0" * 32)


def test_usage_and_quota(ot: OpenType, decision: tuple[str, str]) -> None:
    assert ot.usage.summary().organization_id
    assert ot.usage.quota().organization_id
    # /v1/usage/runs/{id} echoes the id in hyphenated uuid form.
    assert ot.usage.run(decision[0]).run_id.replace("-", "") == decision[0]


async def test_async_get(decision: tuple[str, str]) -> None:
    async with AsyncOpenType() as c:
        assert (await c.runs.get(decision[0])).run_id == decision[0]


# ~20k tokens of varied log lines: roughly 4 characters per token.
LONG_LOG = "\n".join(
    f"2026-09-{1 + i % 28:02d}T{i % 24:02d}:{i % 60:02d}:00Z worker-{i % 17} job={i * 7919 % 100000} "
    f"status={'ok' if i % 13 else 'timeout after 30s'} latency_ms={i * 37 % 900}"
    for i in range(850)
)


def _router_or_skip(ot: OpenType) -> None:
    try:
        ot.router.task_types()
    except NotFoundError:
        pytest.skip("router v2 not deployed")


def test_router(ot: OpenType) -> None:
    _router_or_skip(ot)
    catalog = ot.router.models()
    assert catalog.models
    choice = ot.route("Write a Rust function that parses RFC 3339 timestamps", policy="cost_efficient")
    assert choice.model.id in {m.id for m in catalog.models}
    assert choice.decision_model == "neon-1.1" and choice.run_id
    assert choice.classification.task_type.top and choice.ranking
    top = choice.ranking[0]
    assert top.estimated_cost_usd >= 0 and top.estimated_latency_ms > 0 and top.strengths


def test_router_task_types_and_knobs(ot: OpenType) -> None:
    _router_or_skip(ot)
    tt = ot.router.task_types()
    assert tt.task_types and tt.families and all(t.weights for t in tt.task_types)
    fixed = tt.task_types[0].id
    choice = ot.router.select(
        prompt="Summarize this paragraph in one line.",
        task_type=fixed,
        latency="interactive",
        weights={"quality": 0.5, "cost": 0.3, "speed": 0.2},
    )
    assert choice.classification.task_type.fixed and choice.classification.task_type.label == fixed
    with pytest.raises(BadRequestError) as exc:
        ot.router.select(prompt="x", policy="cost_efficient", weights={"quality": 1.0})
    assert exc.value.code == "weights_require_balanced"


def test_router_long_context(ot: OpenType) -> None:
    _router_or_skip(ot)
    choice = ot.route("Find the root cause of the timeouts in this log:\n" + LONG_LOG)
    assert 12_000 <= choice.input_tokens_est <= 40_000, choice.input_tokens_est
    assert choice.classification.facets.input_tokens_est >= 12_000


def test_decide_long_context(ot: OpenType) -> None:
    run = ot.decide(
        state={"log": LONG_LOG},
        questions={"timeouts": {"type": "noul", "instructions": "does the log show any timeout?"}},
    )
    assert run.state == "completed", run
    assert run.decision is not None and "timeouts" in run.decision.answers
