# OpenType Python SDK

Typed sync and async client for the [OpenType](https://opentype.dev) API: decisions,
verdicts, run streaming, usage, billing, keys and the model router.

Not on PyPI yet. Until the first release, install from GitHub:

```bash
pip install git+https://github.com/OpentypeAI/opentype-python
```

Once released, this becomes `pip install opentype`. Python 3.9+. Dependencies: `httpx`, `pydantic` v2.

Docs: https://docs.opentype.dev. Create an API key at https://console.opentype.dev/keys and export it as `OPENTYPE_API_KEY`.

## Quickstart (sync)

```python
from opentype import OpenType

client = OpenType()  # reads OPENTYPE_API_KEY (and optional OPENTYPE_BASE_URL)

run = client.decide(
    state={"ticket": "everything is down and we have a demo at noon"},
    questions={
        "urgent": {"type": "noul", "instructions": "does this need a reply within the hour?"},
        "queue": {
            "type": "choice",
            "instructions": "which queue?",
            "criteria": {"billing": "payment problems", "technical": None},
        },
    },
)
print(run.decision.answers)  # probabilities per question

verdict = client.verdict(
    messages=[{"role": "user", "content": "Is 'refund me now' a complaint?"}],
    schema={"type": "object", "properties": {"complaint": {"type": "boolean"}}, "required": ["complaint"]},
    max_output_tokens=64,
)
print(verdict.verdict)  # validated against your schema

for past in client.runs.list(limit=50):  # auto-paginates
    print(past.run_id, past.state)
```

## Async

```python
import asyncio
from opentype import AsyncOpenType


async def main() -> None:
    async with AsyncOpenType() as client:
        run = await client.runs.get("run_...")
        async for r in client.runs.list():
            print(r.run_id)


asyncio.run(main())
```

## Stream a run

```python
for event in client.runs.stream(run.run_id):
    print(event.event, event.state)  # "state", then "terminal"
    if event.is_terminal:
        print(event.decision or event.verdict)
```

`client.runs.wait_for(run_id)` blocks until the run is terminal (stream first, then polling).

## Route a task to a model

```python
choice = client.route("Refactor this Rust crate to remove the unsafe blocks", policy="cost_efficient")
print(choice.model.id, choice.reason)
print(choice.classification.task_type.label, choice.classification.task_type.top[:3])

for entry in choice.ranking:  # best first, at most ten
    print(
        entry.id,
        f"quality={entry.expected_quality:.2f} ±{entry.uncertainty:.2f}",
        f"cost=${entry.estimated_cost_usd:.4f}",
        f"latency={entry.estimated_latency_ms:.0f}ms{' (est.)' if entry.latency_estimated else ''}",
    )
    for s in entry.strengths:  # top three benchmarks by contribution
        print("  +", s.name, s.value, f"rank {s.rank}", f"contributes {s.contribution:.3f}")
    for w in entry.weaknesses:  # where it trails the best candidate most
        print("  -", w.name, f"gap {w.gap_to_best:.3f}")

catalog = client.router.models()
task_types = client.router.task_types()  # ids, families and each type's benchmark weights
```

Request knobs (all keyword arguments on `router.select` and `route`):

| | |
| --- | --- |
| `prompt` / `messages` | the task; exactly one |
| `policy` | `balanced` (default), `cost_efficient`, `capability_heavy`, `domain_skills` |
| `task_type` | skip classification and route as this type (from `router.task_types()`); wins over `domain` |
| `domain` | v1 override: route as that domain's default task type |
| `latency` | `interactive`, `standard` (default) or `batch`: how much latency weighs in `balanced` |
| `max_latency_ms` | drop models whose estimated time to the full answer exceeds this, or is unmeasured |
| `weights` | `{"quality", "cost", "speed"}` (or `RouterWeights`), normalized server-side; `balanced` only, else `400 weights_require_balanced` |
| `models` | filters: `include`, `exclude`, `providers`, `open_weights`, `max_price_per_mtok`, `min_context_tokens`, `modalities` |

Reading a ranking entry: `expected_quality` is the task-weighted, normalized (0-1) benchmark quality;
`uncertainty` is the weight resting on imputed values (listed in `imputed`, 0 when all measured).
`estimated_cost_usd` is the price of *this* request (input, expected output, reasoning tokens and turns),
not a per-token rate. Each strength/weakness is a `RouterBenchmarkContribution`: `value` and `rank`
are the published score and catalog rank (null when imputed), `contribution = weight × norm`, and
`gap_to_best` (weaknesses only) is how much that benchmark costs the model versus the best candidate.
The response also carries `threshold` (`q_star`, `r`, `tau`), `filters_applied`, `low_confidence`,
`input_tokens_est`, `catalog_as_of`, `benchmarks_as_of`, `replayed` and the classification `run_id`.

The router only selects; it does not proxy the call. Classification is done by Neon 1.1 and billed
like a decision run. `select` sends an `Idempotency-Key` (pass `idempotency_key=` to choose it), so a
retry after a lost response replays the stored classification instead of paying twice.

Long context: decisions and router tasks accept up to 262,144 input tokens and 4 MiB bodies. The
decision deadline defaults to 30 s plus 120 s per 256k input tokens, capped at 150 s; the client's
default 170 s timeout sits above that cap. `POST /v1/runs` responses carry a `Server-Timing` header
(`admit`, `upstream`, `gateway`, `total`).

## Other resources

| | |
| --- | --- |
| `client.usage` | `summary`, `daily`, `ledger`, `run(run_id)`, `quota()` |
| `client.billing` | `get`, `set_auto_recharge`, `checkout`, `portal` |
| `client.keys` | `list`, `get` with an API key; `create`, `revoke` and `rotate` need a console session |
| `client.router` | `select`, `models`, `task_types` |

Every response is a pydantic model; `obj._request_id` holds the `x-request-id`.

## Configuration

```python
OpenType(
    api_key=None,  # default: OPENTYPE_API_KEY
    base_url=None,  # default: OPENTYPE_BASE_URL or https://api.opentype.dev
    timeout=170.0,  # seconds; above the 150 s max decision deadline
    max_retries=2,
    http_client=None,  # your own httpx.Client / httpx.AsyncClient
)
```

## Retries and idempotency

- Every paid call (`runs.create`, `decide`, `verdict`, `router.select`) sends an `Idempotency-Key`:
  yours if you pass `idempotency_key=`, otherwise a fresh UUID per call.
- No response (network error, timeout): retried with the **same** key, so the run is never duplicated.
- A 5xx on a paid call is **not** retried: the call behind it may already have been charged. Send it
  again with a new key if you want a new attempt. Reads (`GET`) are retried on 5xx.
- Every error from a paid call carries the key it sent in `err.idempotency_key`, generated or yours.
  Sending the same request with that key replays the stored result instead of paying again; a
  router classification still in progress answers `409 classification_not_ready` until it settles.
- 4xx, including 402 and 429, is never retried.
- Backoff: 1, 2, 4 s with full jitter, or the server's `Retry-After`.
- A `202` replay of a run still in flight raises `RunPendingError` (`err.run` has the run): poll it
  with `runs.get` / `runs.wait_for` instead of resubmitting.

## Errors

```python
from opentype import OpenTypeError, InsufficientCreditsError, RateLimitError

try:
    client.decide(...)
except InsufficientCreditsError:
    ...
except OpenTypeError as err:
    print(err.code, err.status, err.request_id, err.violations)
```

| Class | When |
| --- | --- |
| `InvalidRequestError` | 400, 413 (`BadRequestError` alias) |
| `AuthenticationError` | 401 |
| `InsufficientCreditsError` | 402 |
| `PermissionDeniedError` | 403 (e.g. `scope_denied`) |
| `NotFoundError` | 404 |
| `ConflictError` | 409 (`idempotency_conflict`) |
| `RateLimitError` | 429 (`QuotaExceededError` alias) |
| `ServerError` | 5xx; `verdict_schema_violation` carries `violations` |
| `APIConnectionError`, `APITimeoutError` | no response |

Branch on `err.code`, never on the message. Plain-text error bodies map to `http_<status>`.

## Agent tools

The same six tools as the OpenType MCP server (`opentype_decide`, `opentype_verdict`,
`opentype_route_model`, `opentype_list_models`, `opentype_get_run`, `opentype_usage`), as plain dicts —
no dependency on the `openai` or `anthropic` packages.

```python
from opentype.tools import openai_tools, anthropic_tools

tools = openai_tools(client)
completion = openai.chat.completions.create(model=..., messages=msgs, tools=tools.definitions)
for call in completion.choices[0].message.tool_calls or []:
    msgs.append(tools.handle_tool_call(call))   # or tools.handle(name, args) -> JSON string

atools = anthropic_tools(client)
msg = anthropic.messages.create(model=..., tools=atools.definitions, ...)
results = [atools.handle_tool_use(b) for b in msg.content if b.type == "tool_use"]
```

## Development

```bash
uv sync
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
./scripts/generate-types.sh        # regenerate models from openapi.json
OPENTYPE_E2E=1 OPENTYPE_API_KEY=otsk_... uv run pytest tests/test_e2e.py   # live, spends credit
```

## Releasing

`.github/workflows/release.yml` builds and publishes to PyPI with [trusted publishing](https://docs.pypi.org/trusted-publishers/) when a `v*` tag is pushed. It stays unusable until the owner registers a pending publisher on pypi.org (Account settings, Publishing, "Add a new pending publisher"):

| Field | Value |
| --- | --- |
| PyPI project name | `opentype` |
| Owner | `OpentypeAI` |
| Repository name | `opentype-python` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

Then create the `pypi` environment in this repo's settings, bump `src/opentype/_version.py`, and `git tag v0.1.0 && git push --tags`.

## Related

- JavaScript SDK and MCP server: [OpentypeAI/opentype-js](https://github.com/OpentypeAI/opentype-js)
- Claude Code plugin: [OpentypeAI/opentype-claude-plugin](https://github.com/OpentypeAI/opentype-claude-plugin)

## License

Apache-2.0
