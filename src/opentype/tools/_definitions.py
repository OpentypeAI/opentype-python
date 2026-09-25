"""The six agent tools, shared by every adapter and by the MCP server, so they
behave identically everywhere. Schemas are JSON Schema, snake_case."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from .._client import OpenType

POLICIES = ["balanced", "cost_efficient", "capability_heavy", "domain_skills"]
DOMAINS = ["coding", "math", "reasoning", "knowledge", "agentic", "long_context", "writing", "multilingual", "general"]

_MESSAGES = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {"role": {"type": "string", "enum": ["user", "assistant"]}, "content": {"type": "string"}},
        "required": ["role", "content"],
    },
}


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    execute: Callable[[OpenType, Mapping[str, Any]], Any]
    read_only: bool = False


def attr(obj: Any, key: str) -> Any:
    """Read ``key`` from a dict or an SDK object alike."""
    return obj.get(key) if isinstance(obj, dict) else getattr(obj, key)


def _dump(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json", exclude_none=True)
    return obj


def _decide(ot: OpenType, a: Mapping[str, Any]) -> Any:
    return ot.decide(
        state=a["state"],
        questions=a["questions"],
        instructions=a.get("instructions"),
        draws=a.get("draws"),
        model=a.get("model"),
        idempotency_key=a.get("idempotency_key"),
    )


def _verdict(ot: OpenType, a: Mapping[str, Any]) -> Any:
    return ot.verdict(
        messages=a["messages"],
        schema=a["schema"],
        max_output_tokens=int(a["max_output_tokens"]),
        system=a.get("system"),
        deadline_ms=a.get("deadline_ms"),
        idempotency_key=a.get("idempotency_key"),
    )


def _route(ot: OpenType, a: Mapping[str, Any]) -> Any:
    return ot.router.select(
        prompt=a.get("prompt"),
        messages=a.get("messages"),
        policy=a.get("policy"),
        domain=a.get("domain"),
        task_type=a.get("task_type"),
        latency=a.get("latency"),
        max_latency_ms=a.get("max_latency_ms"),
        weights=a.get("weights"),
        models=a.get("models"),
    )


def _list_models(ot: OpenType, a: Mapping[str, Any]) -> Any:
    models = ot.router.models().models
    if a.get("provider"):
        models = [m for m in models if m.provider == a["provider"]]
    if a.get("open_weights") is not None:
        models = [m for m in models if m.open_weights == bool(a["open_weights"])]
    if a.get("domain"):
        models = [m for m in models if a["domain"] in m.domains]
    if a.get("limit"):
        models = models[: int(a["limit"])]
    return {"models": [_dump(m) for m in models]}


def _get_run(ot: OpenType, a: Mapping[str, Any]) -> Any:
    return ot.runs.get(str(a["run_id"]))


def _rfc3339(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _usage(ot: OpenType, a: Mapping[str, Any]) -> Any:
    start, end = a.get("start_at"), a.get("end_at")
    if not start and not end:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        start, end = _rfc3339(now - timedelta(days=30)), _rfc3339(now)
    out: dict[str, Any] = {"usage": _dump(ot.usage.summary(start_at=start, end_at=end))}
    if a.get("include_quota"):
        out["quota"] = _dump(ot.usage.quota())
    return out


TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        "opentype_decide",
        "Ask Neon 1.1 calibrated questions about a state (yes/no, choice, score) and get probabilities "
        "per question. Spends credit.",
        {
            "type": "object",
            "properties": {
                "state": {"description": "The thing being decided about: any JSON, or a string."},
                "questions": {
                    "type": "object",
                    "description": "Question id -> {type: noul|choice|score, instructions, criteria?, depends_on?, "
                    "ask_if?}. choice criteria: {option: description|null}; score criteria: [levels].",
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["noul", "choice", "score"]},
                            "instructions": {"type": "string"},
                            "criteria": {},
                            "depends_on": {"type": "array", "items": {"type": "string"}},
                            "ask_if": {"type": "object"},
                        },
                        "required": ["type", "instructions"],
                    },
                },
                "instructions": {"type": "string"},
                "draws": {"type": "integer", "minimum": 1, "maximum": 8},
                "model": {"type": "string", "enum": ["neon-1.1", "neon-latest"]},
                "idempotency_key": {"type": "string"},
            },
            "required": ["state", "questions"],
        },
        _decide,
    ),
    ToolDefinition(
        "opentype_verdict",
        "Get a JSON document that is validated against your JSON Schema before it is returned. Spends credit.",
        {
            "type": "object",
            "properties": {
                "messages": _MESSAGES,
                "system": {"type": "string"},
                "schema": {"type": "object", "description": "JSON Schema the answer must satisfy."},
                "max_output_tokens": {"type": "integer", "minimum": 1},
                "deadline_ms": {"type": "integer", "minimum": 1},
                "idempotency_key": {"type": "string"},
            },
            "required": ["messages", "schema", "max_output_tokens"],
        },
        _verdict,
    ),
    ToolDefinition(
        "opentype_route_model",
        "Pick the best LLM for a task from the benchmark catalog, by policy. Returns the model id, the reason "
        "and the top ranking. Pass prompt or messages, not both. Spends credit (one classification).",
        {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
                "messages": _MESSAGES,
                "policy": {"type": "string", "enum": POLICIES},
                "domain": {"type": "string", "enum": DOMAINS},
                "task_type": {"type": "string", "description": "Fix the task type; see GET /v1/router/task-types."},
                "latency": {"type": "string", "enum": ["interactive", "standard", "batch"]},
                "max_latency_ms": {"type": "number"},
                "weights": {
                    "type": "object",
                    "description": "balanced policy only.",
                    "properties": {
                        "quality": {"type": "number"},
                        "cost": {"type": "number"},
                        "speed": {"type": "number"},
                    },
                },
                "models": {
                    "type": "object",
                    "properties": {
                        "include": {"type": "array", "items": {"type": "string"}},
                        "exclude": {"type": "array", "items": {"type": "string"}},
                        "providers": {"type": "array", "items": {"type": "string"}},
                        "open_weights": {"type": "boolean"},
                        "max_price_per_mtok": {"type": "number"},
                        "min_context_tokens": {"type": "integer"},
                        "modalities": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
        },
        _route,
    ),
    ToolDefinition(
        "opentype_list_models",
        "List the router's model catalog with prices and benchmark scores, optionally filtered.",
        {
            "type": "object",
            "properties": {
                "provider": {"type": "string"},
                "open_weights": {"type": "boolean"},
                "domain": {"type": "string", "enum": DOMAINS},
                "limit": {"type": "integer", "minimum": 1},
            },
        },
        _list_models,
        read_only=True,
    ),
    ToolDefinition(
        "opentype_get_run",
        "Fetch a run by id: state, answer, usage and cost.",
        {"type": "object", "properties": {"run_id": {"type": "string"}}, "required": ["run_id"]},
        _get_run,
        read_only=True,
    ),
    ToolDefinition(
        "opentype_usage",
        "Usage and spend for a window (default: last 30 days, UTC), optionally with the quota.",
        {
            "type": "object",
            "properties": {
                "start_at": {"type": "string", "format": "date-time"},
                "end_at": {"type": "string", "format": "date-time"},
                "include_quota": {"type": "boolean"},
            },
        },
        _usage,
        read_only=True,
    ),
]

TOOLS_BY_NAME = {t.name: t for t in TOOLS}


class ToolSet:
    """Definitions plus a dispatcher. ``handle`` returns the tool's JSON output as
    a string; API errors come back as ``{"error": {...}}`` so the model can react."""

    definitions: list[dict[str, Any]]

    def __init__(self, client: Optional[OpenType], definitions: list[dict[str, Any]]) -> None:
        self._client = client
        self.definitions = definitions

    @property
    def client(self) -> OpenType:
        if self._client is None:
            self._client = OpenType()
        return self._client

    def call(self, name: str, args: Optional[Mapping[str, Any]] = None) -> Any:
        tool = TOOLS_BY_NAME.get(name)
        if tool is None:
            raise KeyError(f"unknown tool {name!r}")
        return _dump(tool.execute(self.client, args or {}))

    def handle(self, name: str, args: Any = None) -> str:
        from .._exceptions import OpenTypeError

        if name not in TOOLS_BY_NAME:
            raise KeyError(f"unknown tool {name!r}")
        try:
            if isinstance(args, str):
                args = json.loads(args)
            if args is not None and not isinstance(args, Mapping):
                raise TypeError("tool arguments must be a JSON object")
            return json.dumps(self.call(name, args))
        except (ValueError, TypeError, KeyError) as exc:
            # Malformed model arguments answer the tool call instead of ending the agent loop.
            return json.dumps({"error": {"code": "invalid_arguments", "message": str(exc)}})
        except OpenTypeError as exc:
            return json.dumps(
                {
                    "error": {
                        "code": exc.code,
                        "message": exc.message,
                        "status": exc.status,
                        "request_id": exc.request_id,
                    }
                }
            )
