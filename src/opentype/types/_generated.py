# Generated from openapi.json by scripts/generate-types.sh. Do not edit.

from __future__ import annotations

from typing import Any, Literal, Optional, Union

from opentype._models import BaseModel
from pydantic import ConfigDict, Field, RootModel


class AutoRechargeRequest(BaseModel):
    model_config = ConfigDict(
        extra='allow',
    )
    enabled: bool
    threshold_micros: Optional[int] = Field(
        None,
        description='Required when `enabled` is `true`. At most 1,000,000,000.',
        ge=0,
    )
    amount_micros: Optional[int] = Field(
        None,
        description='Required when `enabled` is `true`. 5,000,000 to 1,000,000,000, in whole cents.',
        ge=0,
    )


class AutoRechargeSettings(BaseModel):
    model_config = ConfigDict(
        extra='allow',
    )
    enabled: bool
    threshold_micros: Optional[int] = Field(None, ge=0)
    amount_micros: Optional[int] = Field(None, ge=0)


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(
        extra='allow',
    )
    amount_micros: int = Field(
        ...,
        description='5,000,000 to 1,000,000,000 ($5 to $1,000), a multiple of 10,000 (whole cents).',
        ge=0,
    )


class CheckoutResponse(BaseModel):
    model_config = ConfigDict(
        extra='allow',
    )
    checkout_url: str


class DailyUsageBody(BaseModel):
    """
    One day of `GET /v1/usage/daily`.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    date: str = Field(..., description='`YYYY-MM-DD`, UTC.')
    runs: int = Field(..., ge=0)
    input_tokens: int = Field(..., ge=0)
    output_tokens: int = Field(..., ge=0)
    spend_micros: int = Field(..., ge=0)


class DecisionResponse(BaseModel):
    """
    A decision's answers.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    answers: Any = Field(
        ...,
        description='One answer per question, keyed by your question ids. Shapes by `type`: `noul` has `probability`, which is P(yes); `choice` has `choice`, `probabilities` keyed by option name, and `confidence`; `score` has `score` (the expected 0-based level index), `legend`, `probabilities` keyed by index, and `confidence`; `skipped` has `because` (`question`, `answered` when known, `required`) when an `ask_if` failed. Any answer may carry `label_mass` and `answered_within_labels`. Every probability and confidence is between 0 and 1.',
    )
    draws: int = Field(..., description='Reads averaged.', ge=0)
    read: Literal['slot_constrained', 'reconstructed'] = Field(
        ...,
        description='What constrained the answers. Only `slot_constrained` is produced today.',
    )
    model: Optional[str] = Field(
        None,
        description='Live responses only. The model that served the run: `neon-1.1`.',
        examples=['neon-1.1'],
    )
    stages: Optional[list[list[str]]] = Field(
        None,
        description='Live responses only. Question ids per stage, in the order the stages ran.',
    )
    thought_tokens: Optional[int] = Field(
        None,
        description='Live responses only, when thought tokens were generated. The thought text is never returned.',
        ge=0,
    )
    thought_closed: Optional[bool] = None


class HealthResponse(BaseModel):
    model_config = ConfigDict(
        extra='allow',
    )
    status: str
    service: str


class KeyPrincipal1(BaseModel):
    """
    A human member. The value is the user identifier.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    id: str = Field(..., description="The user's id.")
    type: Literal['user']


class KeyPrincipal2(BaseModel):
    """
    A machine identity owned by the organization. At most 64 characters
    of `[A-Za-z0-9_-]`; the service prefixes `svc_` when it is missing.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    id: str = Field(..., description='An id you choose for the service account.')
    type: Literal['service_account']


class NoulCriteria(BaseModel):
    """
    What each side of a yes/no question means. Both are optional.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    true: Optional[str] = None
    false: Optional[str] = None


class PortalResponse(BaseModel):
    model_config = ConfigDict(
        extra='allow',
    )
    portal_url: str


class QuotaLimitsBody(BaseModel):
    """
    The limits half of `GET /v1/quota`. A null limit is "no organization-level
    limit is configured"; `request_spend_ceiling_micros` is never null.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    period_spend_limit_micros: Optional[int] = Field(None, ge=0)
    period_token_limit: Optional[int] = Field(None, ge=0)
    request_spend_ceiling_micros: int = Field(
        ...,
        description='The per-run spend ceiling, at most 20,000 micro-USD. Each run holds this much until it settles.',
        ge=0,
    )


class RouterBenchmarkContribution(BaseModel):
    """
    One benchmark's part in a candidate's expected quality.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    benchmark: str = Field(..., examples=['swe_bench_verified'])
    name: str = Field(..., examples=['SWE-bench Verified'])
    value: Optional[float] = Field(
        None, description='The published value, null when imputed.'
    )
    rank: Optional[int] = Field(
        None,
        description='Rank among catalog models with a published value, null when imputed.',
        ge=0,
    )
    norm: float = Field(..., description='Normalized value, 0-1.')
    weight: float = Field(..., description='Weight of the benchmark for this task.')
    contribution: float = Field(..., description='weight × norm.')
    gap_to_best: Optional[float] = Field(
        None, description='Weaknesses only: weight × (this model − the best candidate).'
    )


class RouterBenchmarkHighlight(BaseModel):
    """
    A benchmark where a model ranks in the catalog's top three.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    benchmark: str
    name: str
    value: float
    rank: int = Field(..., ge=0)
    of: int = Field(..., description='Models with a published value.', ge=0)


class RouterFilterCount(BaseModel):
    """
    How many models one filter removed.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    filter: str
    removed: int = Field(..., ge=0)


class RouterImputed(BaseModel):
    """
    A benchmark value that was imputed for a candidate.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    benchmark: str
    rule: str = Field(..., description='`correlated`, `family` or `index`.')
    from_: Optional[str] = Field(None, alias='from')


class RouterLabel(BaseModel):
    """
    One classified label and the distribution it was the argmax of.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    label: str
    probabilities: dict[str, float] = Field(
        ...,
        description='Probability per label. For a caller-fixed label this is that label at\n`1.0`.',
    )


class RouterModelFilters(BaseModel):
    """
    Filters over the catalog. All optional; an empty object keeps every model.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    include: Optional[list[str]] = Field(
        None,
        description='Only these model ids. An id the catalog does not list is `400`\n`unknown_model_id`.',
    )
    exclude: Optional[list[str]] = Field(
        None, description='Never these model ids. Same check as `include`.'
    )
    providers: Optional[list[str]] = Field(
        None, description='Only these providers, e.g. `openai`, case-insensitive.'
    )
    open_weights: Optional[bool] = Field(
        None, description='`true`: open-weights models only; `false`: closed only.'
    )
    max_price_per_mtok: Optional[float] = Field(
        None,
        description='Maximum blended price (3:1 input:output), USD per million tokens.',
    )
    min_context_tokens: Optional[int] = Field(None, ge=0)
    modalities: Optional[list[str]] = Field(
        None,
        description='Every listed modality must be supported: `text`, `image`, `audio`,\n`video`.',
    )


class RouterModelRef(BaseModel):
    """
    A model, as a selection names it.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    id: str = Field(..., examples=['gpt-6-sol'])
    name: str = Field(..., examples=['GPT-6 Sol'])
    provider: str = Field(..., examples=['openai'])
    open_weights: bool


class RouterRankingEntry(BaseModel):
    """
    One ranked candidate.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    id: str
    name: str
    provider: str
    open_weights: bool
    score: float = Field(
        ...,
        description="The policy's sort key, higher is better. For `cost_efficient` it is\nthe negated estimated cost.",
    )
    blended_price_per_mtok: float
    domain_score: float = Field(..., description='v1 name for `expected_quality`.')
    expected_quality: float = Field(
        ...,
        description='Weighted normalized benchmark quality for this task, 0-1, minus the\nimputation penalty.',
    )
    uncertainty: float = Field(
        ...,
        description='Weight on imputed values: 0 when every benchmark was measured.',
    )
    estimated_cost_usd: float = Field(
        ...,
        description='USD for this request: input, expected output, reasoning tokens and\nexpected turns.',
    )
    estimated_latency_ms: float = Field(
        ..., description='Milliseconds to the full answer.'
    )
    latency_estimated: bool = Field(
        ..., description='A catalog median stood in for a missing speed or TTFT.'
    )
    strengths: list[RouterBenchmarkContribution] = Field(
        ..., description='Top three benchmarks by contribution.'
    )
    weaknesses: list[RouterBenchmarkContribution] = Field(
        ..., description='Up to two benchmarks where it trails the best candidate most.'
    )
    imputed: list[RouterImputed]


class RouterScores(BaseModel):
    """
    Benchmark scores, 0-100, null when unknown.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    intelligence: float
    coding: Optional[float] = None
    math: Optional[float] = None
    reasoning: Optional[float] = None
    knowledge: Optional[float] = None
    agentic: Optional[float] = None
    long_context: Optional[float] = None
    instruction_following: Optional[float] = None
    multilingual: Optional[float] = None


class RouterTaskTypeProbability(BaseModel):
    """
    One task type and its probability.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    task_type: str = Field(..., examples=['code_generation'])
    family: str = Field(..., examples=['coding'])
    probability: float


class RouterTaskWeight(BaseModel):
    """
    One benchmark in a task type's weight vector.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    benchmark: str
    name: str
    weight: float


class RouterThreshold(BaseModel):
    """
    The quality bar in force (`balanced`, `cost_efficient`).
    """

    model_config = ConfigDict(
        extra='allow',
    )
    q_star: float = Field(
        ..., description='Best expected quality among the filtered models.'
    )
    r: float = Field(..., description='Required share of `q_star` at this difficulty.')
    tau: float


class RouterWeights(BaseModel):
    """
    The caller's own `balanced` trade-off, normalized to sum to 1.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    quality: Optional[float] = None
    cost: Optional[float] = None
    speed: Optional[float] = None


class RunCountsBody(BaseModel):
    model_config = ConfigDict(
        extra='allow',
    )
    total: int = Field(..., ge=0)
    completed: int = Field(..., ge=0)
    failed: int = Field(..., ge=0)
    in_flight: int = Field(..., ge=0)


class RunMessage(BaseModel):
    """
    One prompt turn. Unknown keys are refused.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    role: Literal['user', 'assistant']
    content: str


class RunsErrorDetail(BaseModel):
    model_config = ConfigDict(
        extra='allow',
    )
    code: str = Field(
        ..., description='Stable snake_case code. The only field to branch on.'
    )
    message: str
    request_id: str
    violations: Optional[list[str]] = Field(
        None,
        description='Only on `verdict_schema_violation`: up to 10 JSON Pointers into the rejected document.',
    )


class SharedQuestionFields(BaseModel):
    """
    Optional fields every question type accepts.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    depends_on: Optional[list[str]] = Field(
        None,
        description='Ids of other questions in this set that must be answered in an earlier stage. Cycles are refused.',
    )
    ask_if: Optional[dict[str, list[str]]] = Field(
        None,
        description='Question id to the answer names that make this question worth asking. When the condition fails, the answer is `skipped`.',
    )
    alone: Optional[bool] = Field(
        None,
        description='Read this question on its own rather than jointly with its stage.',
    )


class SpendTotalsBody(BaseModel):
    model_config = ConfigDict(
        extra='allow',
    )
    reserved_micros: int = Field(..., ge=0)
    settled_micros: int = Field(..., ge=0)
    unsettled_micros: int = Field(
        ..., description='`reserved_micros` minus `settled_micros`, floored at 0.', ge=0
    )


class TokenTotalsBody(BaseModel):
    model_config = ConfigDict(
        extra='allow',
    )
    input_tokens: int = Field(..., ge=0)
    output_tokens: int = Field(..., ge=0)
    total_tokens: int = Field(..., ge=0)


class UsageResponse(BaseModel):
    """
    Tokens the run used.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    input_tokens: int = Field(..., ge=0)
    output_tokens: int = Field(..., ge=0)


class UsageWindowBody(BaseModel):
    model_config = ConfigDict(
        extra='allow',
    )
    start_at: str
    end_at: str


class BillingTransaction(BaseModel):
    model_config = ConfigDict(
        extra='allow',
    )
    id: str
    kind: Literal['purchase', 'grant', 'usage', 'refund', 'adjustment']
    amount_micros: int = Field(
        ..., description='Signed: positive adds credit, negative spends it.'
    )
    description: str
    created_at: str


class CreateKeyRequest(BaseModel):
    model_config = ConfigDict(
        extra='allow',
    )
    name: str = Field(..., description='A label shown in the console. Not unique.')
    scopes: list[
        Literal[
            'runs_read',
            'runs_write',
            'keys_read',
            'keys_write',
            'members_read',
            'members_write',
            'billing_read',
            'billing_write',
            'usage_read',
        ]
    ] = Field(..., description='At least one scope, each held by the caller.')
    principal: Optional[Union[KeyPrincipal1, KeyPrincipal2]] = None


class CreateRunRequest(BaseModel):
    """
    A run. `kind` selects a decision (`state` plus `questions`) or a verdict (`messages` plus `schema`), and defaults to `verdict`. `max_output_tokens` is required on every run. Unknown fields are refused, and a field that belongs to the other kind is `400 invalid_body`.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    kind: Optional[Literal['verdict', 'decision']] = Field(
        None,
        description='`decision` or `verdict`. Defaults to `verdict`, so send `decision` explicitly for a decision run.',
    )
    system: Optional[str] = None
    messages: Optional[list[RunMessage]] = Field(
        None,
        description='Verdict runs only, and required for them. At least one prompt turn.',
    )
    schema_: Optional[Any] = Field(
        None,
        alias='schema',
        description='Verdict runs only, and required for them. The JSON Schema the verdict must satisfy: an object of at most 32 KiB, nesting depth 12, 64 subschemas and 512 properties, `pattern` values of at most 256 characters, and only local `#` references. Out of bounds is `400 invalid_verdict_schema`.',
    )
    state: Optional[Any] = Field(
        None,
        description='Decision runs only, and required for them. What is being decided about: any JSON value. A string is sent as-is; anything else as its JSON text.',
    )
    instructions: Optional[str] = Field(
        None, description='Decision runs only. Context that applies to every question.'
    )
    questions: Optional[dict[str, Any]] = Field(
        None,
        description='Decision runs only, and required for them. 1 to 64 questions keyed by your own ids. An id must be non-empty and must not contain `:` or a newline. Out of bounds is `400 invalid_decision_questions`.',
    )
    draws: Optional[int] = Field(
        None,
        description='Decision runs only. Independent reads to average, 1 to 8. Defaults to 1.',
        ge=0,
    )
    think_tokens: Optional[int] = Field(
        None,
        description='Decision runs only. Tokens the model may think before answering, 0 to 4096. Defaults to 0. The thought text is never returned.',
        ge=0,
    )
    model: Optional[str] = Field(
        None,
        description='Decision runs only. `neon-1.1`, or `neon-latest`, which resolves to `neon-1.1`. Any other value is `400 unknown_model`.',
        examples=['neon-1.1'],
    )
    capability_hint: Optional[
        list[
            Literal[
                'chat',
                'reasoning',
                'tools',
                'vision',
                'streaming',
                'embedding',
                'structured_read',
            ]
        ]
    ] = Field(
        None,
        description='Optional routing hints. At most 7, no duplicates. Hints can only narrow routing. Hint errors are reported as `invalid_verdict_schema` on either kind.',
    )
    max_output_tokens: int = Field(
        ...,
        description='Required. Output tokens the run may generate, greater than 0. Counts toward the token quota estimate.',
        ge=0,
    )
    deadline_ms: Optional[int] = Field(
        None,
        description='Time budget in milliseconds. A verdict run defaults to 30,000 and is clamped to 1 to 120,000. A decision run defaults to 30,000 plus 120,000 per 262,144 input tokens and is clamped to 1 to 150,000. Past it the run is `504 deadline_exceeded`.',
        ge=0,
    )
    question_order: Optional[list[str]] = Field(
        None,
        description='Decision runs only. Your question order; it must name exactly the keys of `questions`. Defaults to sorted key order.',
    )


class DailyUsageResponse(BaseModel):
    """
    `GET /v1/usage/daily`.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    organization_id: str
    window: UsageWindowBody
    days: list[DailyUsageBody] = Field(
        ...,
        description='One row per UTC day, oldest first. Days without activity are present at zero.',
    )


class DecisionQuestionRequest1(SharedQuestionFields):
    """
    A yes/no question. Its answer names are `yes` and `no`; the answer's `probability` is P(yes).
    """

    model_config = ConfigDict(
        extra='allow',
    )
    instructions: str
    criteria: Optional[NoulCriteria] = None
    type: Literal['noul']


class DecisionQuestionRequest2(SharedQuestionFields):
    """
    A closed option set. The option names are the answer names.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    instructions: str
    criteria: dict[str, Optional[str]]
    type: Literal['choice']


class DecisionQuestionRequest3(SharedQuestionFields):
    """
    Ordered levels. Answers are keyed by 0-based level index.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    instructions: str
    criteria: list[str]
    type: Literal['score']


class DecisionQuestionRequest(
    RootModel[
        Union[
            DecisionQuestionRequest1, DecisionQuestionRequest2, DecisionQuestionRequest3
        ]
    ]
):
    root: Union[
        DecisionQuestionRequest1, DecisionQuestionRequest2, DecisionQuestionRequest3
    ] = Field(
        ...,
        description='One question, selected by `type`: `noul` (yes or no), `choice` (a closed option set) or `score` (ordered levels). Each needs 2 to 20 alternatives with unique names; `noul` always has 2. Unknown keys are refused.',
    )


class KeyResponse(BaseModel):
    """
    A key without its secret.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    id: str
    name: str
    principal: Union[KeyPrincipal1, KeyPrincipal2] = Field(
        ...,
        description='Who a key acts as: a user, or a service account owned by the organization.',
    )
    scopes: list[
        Literal[
            'runs_read',
            'runs_write',
            'keys_read',
            'keys_write',
            'members_read',
            'members_write',
            'billing_read',
            'billing_write',
            'usage_read',
        ]
    ]
    state: Literal['active', 'revoked'] = Field(
        ..., description='A revoked key is kept, never deleted.'
    )
    secret_prefix: str = Field(
        ...,
        description='The first 13 characters of the secret (`otsk_` plus 8), for display.',
    )
    created_by: str
    created_at: str
    last_used_at: Optional[str] = None
    revoked_at: Optional[str] = None


class KeyWithSecretResponse(KeyResponse):
    """
    A key with its secret. Only create and rotate return this.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    secret: str = Field(
        ...,
        description='The plaintext secret. Shown once. The service stores only its SHA-256\nand cannot return this value again; a lost secret is rotated, not\nrecovered.',
    )


class LedgerEntryBody(BaseModel):
    """
    One model attempt.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    run_id: str
    retry_ordinal: int = Field(..., ge=0)
    provider: str
    model_id: str
    provider_request_id: Optional[str] = None
    status: str
    tokens: TokenTotalsBody
    cost_micros: int = Field(..., ge=0)
    created_at: str


class LedgerResponse(BaseModel):
    """
    `GET /v1/usage/ledger`.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    organization_id: str
    window: UsageWindowBody
    limit: int = Field(..., ge=0)
    entries: list[LedgerEntryBody]


class OrganizationUsageResponse(BaseModel):
    """
    `GET /v1/usage`.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    organization_id: str
    window: UsageWindowBody
    runs: RunCountsBody
    tokens: TokenTotalsBody
    spend: SpendTotalsBody


class QuotaResponse(BaseModel):
    """
    `GET /v1/quota`.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    organization_id: str
    period: UsageWindowBody
    limits: QuotaLimitsBody
    consumed_tokens: TokenTotalsBody
    consumed_spend: SpendTotalsBody
    remaining_spend_micros: Optional[int] = Field(
        None,
        description='The spend limit minus the larger of settled and reserved spend, floored at 0. `null` when there is no spend limit.',
        ge=0,
    )
    remaining_tokens: Optional[int] = Field(None, ge=0)


class RouterCatalogModel(BaseModel):
    """
    One catalog model.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    id: str
    name: str
    provider: str
    open_weights: bool
    license: Optional[str] = None
    released: Optional[str] = None
    context_tokens: int = Field(..., ge=0)
    modalities: list[str]
    price_input_per_mtok: float
    price_output_per_mtok: float
    blended_price_per_mtok: float
    output_tokens_per_s: Optional[float] = None
    ttft_ms: Optional[float] = None
    reasoning_token_factor: float = Field(
        ...,
        description='Output tokens emitted per visible output token, relative to the\ncatalog median; at least 1.',
    )
    scores: RouterScores
    domains: list[str] = Field(
        ...,
        description='Domains where the model is a specialist (top quartile of the catalog).',
    )
    highlights: list[RouterBenchmarkHighlight] = Field(
        ...,
        description='Benchmarks where it ranks top three, best rank first, at most eight.',
    )
    benchmarks_measured: int = Field(
        ..., description='Benchmarks with a published value for this model.', ge=0
    )


class RouterFacets(BaseModel):
    """
    The facets the ranking conditions on.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    difficulty_expected: float = Field(
        ...,
        description='Expected level on the 0-3 scale (trivial, standard, hard, expert),\nafter the safety floor.',
    )
    difficulty: RouterLabel = Field(
        ..., description='`trivial`, `standard`, `hard` or `expert`.'
    )
    output_length: RouterLabel = Field(
        ..., description='`short`, `medium`, `long` or `huge`.'
    )
    output_tokens_est: float = Field(..., description='Expected visible output tokens.')
    needs_tools: float
    needs_vision: float
    safety_sensitive: float
    language: str = Field(
        ...,
        description='Language the task is written in: `en`, `fr`, `zh`, `es` or `other`.',
    )
    target_language: Optional[str] = Field(
        None, description='Translation target, when the task asks for one.'
    )
    input_tokens_est: int = Field(..., ge=0)


class RouterModelsResponse(BaseModel):
    model_config = ConfigDict(
        extra='allow',
    )
    as_of: str
    benchmarks_as_of: str
    source: str
    domains: list[str]
    task_types: list[str]
    policies: list[str]
    models: list[RouterCatalogModel]


class RouterSelectRequest(BaseModel):
    """
    A selection request: the task, as `prompt` or as `messages` (exactly one).
    """

    model_config = ConfigDict(
        extra='allow',
    )
    prompt: Optional[str] = Field(
        None,
        description='The task. Bodies up to 4 MiB are accepted; only the head and tail of the task are read to classify it.',
    )
    messages: Optional[list[RunMessage]] = Field(
        None,
        description='The task as conversation turns, joined into one text as for `prompt`.',
    )
    policy: Optional[str] = Field(
        None,
        description='`balanced` (default), `cost_efficient`, `capability_heavy` or\n`domain_skills`. Anything else is `400` `invalid_policy`.',
        examples=['balanced'],
    )
    domain: Optional[str] = Field(
        None,
        description="v1 override: route as this domain's default task type (`coding`,\n`math`, `reasoning`, `knowledge`, `agentic`, `long_context`,\n`writing`, `multilingual` or `general`). The task type is then not\nclassified; difficulty and the facets still are.",
    )
    task_type: Optional[str] = Field(
        None,
        description='Skip task-type classification and route as this task type (see\n`GET /v1/router/task-types`). Wins over `domain`.',
        examples=['code_generation'],
    )
    latency: Optional[str] = Field(
        None,
        description='`interactive`, `standard` (default) or `batch`: how much estimated\nlatency weighs in `balanced`.',
        examples=['standard'],
    )
    max_latency_ms: Optional[float] = Field(
        None,
        description='Drop models whose estimated time to the full answer exceeds this, or\nwhose speed is not measured.',
    )
    weights: Optional[RouterWeights] = None
    models: Optional[RouterModelFilters] = None


class RouterTaskType(BaseModel):
    """
    The task-type distribution: the argmax and the five most probable.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    label: str = Field(..., examples=['code_generation'])
    family: str
    top: list[RouterTaskTypeProbability] = Field(
        ...,
        description='The five most probable types, most probable first. The ranking mixes\nevery type at 5% or more.',
    )
    fixed: bool = Field(
        ...,
        description='True when the caller fixed the task type (`task_type` or `domain`).',
    )


class RouterTaskTypeInfo(BaseModel):
    """
    A task type the router classifies into.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    id: str = Field(..., examples=['code_generation'])
    family: str = Field(..., examples=['coding'])
    domain: str = Field(..., description='The v1 domain it reports as.')
    description: str
    turns: float = Field(
        ..., description='Expected model turns; agentic types are multi-turn.'
    )
    weights: list[RouterTaskWeight] = Field(
        ..., description='The benchmark vector, primary first.'
    )


class RouterTaskTypesResponse(BaseModel):
    model_config = ConfigDict(
        extra='allow',
    )
    benchmarks_as_of: str
    families: list[str]
    task_types: list[RouterTaskTypeInfo]


class RunResponse(BaseModel):
    """
    A run. A completed run carries `verdict` or `decision`, never both. Absent optional fields are omitted, not `null`. Stored reads (replays, retrieve, stream, list rows) omit `cost_basis` and `schema_enforcement`; list rows also omit the answer, `usage` and cost.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    run_id: str = Field(..., description='`run_` followed by 32 hex characters.')
    kind: Literal['verdict', 'decision'] = Field(
        ...,
        description='Which kind of answer this run produces: look at `verdict` or at `decision`.',
    )
    state: Literal['pending', 'running', 'completed', 'failed']
    input_digest: str = Field(
        ...,
        description='64-character hex SHA-256 of the normalized input, kind and contract.',
    )
    output_digest: Optional[str] = None
    verdict: Optional[Any] = Field(
        None,
        description='Completed verdict runs: your JSON document, validated against your schema.',
    )
    decision: Optional[DecisionResponse] = None
    usage: Optional[UsageResponse] = None
    cost_micros: Optional[int] = Field(None, ge=0)
    cost_basis: Optional[Literal['provider_reported', 'estimated']] = None
    schema_enforcement: Optional[
        Literal['unconstrained', 'requested', 'forced', 'enforced']
    ] = None
    replayed: bool = Field(
        ...,
        description='`true` whenever the body came from storage: every replay, retrieve, stream and list row. A replay is never charged again.',
    )


class RunUsageResponse(BaseModel):
    """
    `GET /v1/usage/runs/{run_id}`.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    run_id: str
    organization_id: str
    state: str
    created_at: str
    tokens: TokenTotalsBody
    spend: SpendTotalsBody
    ceiling_micros: int = Field(..., ge=0)
    attempts: list[LedgerEntryBody]


class RunsErrorBody(BaseModel):
    """
    The error envelope, shared by every route. Branch on `error.code`.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    error: RunsErrorDetail


class BillingResponse(BaseModel):
    model_config = ConfigDict(
        extra='allow',
    )
    organization_id: str
    balance_micros: int = Field(
        ...,
        description='Signed. Credits, minus settled spend, minus what unsettled runs hold.',
    )
    currency: Literal['usd']
    auto_recharge: AutoRechargeSettings
    has_payment_method: bool
    transactions: list[BillingTransaction] = Field(
        ..., description='Newest first, at most 50.'
    )


class KeyListResponse(BaseModel):
    model_config = ConfigDict(
        extra='allow',
    )
    keys: list[KeyResponse]


class RouterClassification(BaseModel):
    model_config = ConfigDict(
        extra='allow',
    )
    domain: RouterLabel = Field(
        ..., description='v1 vocabulary, derived from the task-type distribution.'
    )
    difficulty: RouterLabel = Field(
        ...,
        description='v1 vocabulary (`easy`, `medium`, `hard`), derived from the level.',
    )
    task_type: RouterTaskType
    facets: RouterFacets


class RouterSelectResponse(BaseModel):
    model_config = ConfigDict(
        extra='allow',
    )
    id: str = Field(
        ...,
        description='`rtr_` plus the uuid of the classification run.',
        examples=['rtr_0f8e3c1a9b2d4e5f8a7b6c5d4e3f2a1b'],
    )
    run_id: str = Field(
        ...,
        description='The classification run, readable at `/v1/runs/{run_id}` and in usage.',
    )
    policy: str
    model: RouterModelRef
    classification: RouterClassification
    ranking: list[RouterRankingEntry] = Field(
        ..., description='Top candidates, best first, at most ten.'
    )
    score_basis: Literal['domain', 'intelligence', 'benchmarks'] = Field(
        ...,
        description="Which benchmarks decided. v2 always decides on the task's weighted\nbenchmark vector; `domain` and `intelligence` are the v1 values.",
    )
    difficulty_floor: Optional[float] = Field(
        None, description='v1 name for `threshold.tau` (`balanced`, `cost_efficient`).'
    )
    threshold: Optional[RouterThreshold] = None
    filters_applied: list[RouterFilterCount] = Field(
        ...,
        description='Filters that removed at least one model, in the order applied.',
    )
    low_confidence: bool = Field(
        ..., description='`domain_skills` with a most probable task type under 40%.'
    )
    input_tokens_est: int = Field(..., ge=0)
    reason: str
    decision_model: str = Field(..., examples=['neon-1.1'])
    catalog_as_of: str = Field(..., description='The catalog snapshot date.')
    benchmarks_as_of: str = Field(..., description='The benchmark snapshot date.')
    usage: Optional[UsageResponse] = None
    cost_micros: Optional[int] = Field(None, ge=0)
    replayed: bool = Field(
        ...,
        description='True when an `Idempotency-Key` replayed a stored classification.',
    )


class RunListResponse(BaseModel):
    """
    A page of runs, newest first.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    runs: list[RunResponse]
    limit: int = Field(
        ..., description='The limit applied, after clamping to 1 to 100.', ge=0
    )
    offset: int = Field(..., ge=0)
