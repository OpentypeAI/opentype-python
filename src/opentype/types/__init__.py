from __future__ import annotations

from typing import Any, Literal, Optional

from .._models import BaseModel
from ._generated import *  # noqa: F403
from ._generated import (
    RouterBenchmarkContribution,
    RouterBenchmarkHighlight,
    RouterCatalogModel,
    RouterClassification,
    RouterFacets,
    RouterFilterCount,
    RouterImputed,
    RouterLabel,
    RouterModelFilters,
    RouterModelRef,
    RouterModelsResponse,
    RouterRankingEntry,
    RouterScores,
    RouterSelectRequest,
    RouterSelectResponse,
    RouterTaskType,
    RouterTaskTypeInfo,
    RouterTaskTypeProbability,
    RouterTaskTypesResponse,
    RouterTaskWeight,
    RouterThreshold,
    RouterWeights,
    RunResponse,
)

# Pre-v2 public names, kept as aliases of the generated models.
RouterCatalog = RouterModelsResponse
RouterModel = RouterCatalogModel

# Vocabularies the server validates; the generated models keep them as ``str``.
RouterPolicy = Literal["balanced", "cost_efficient", "capability_heavy", "domain_skills"]
RouterDomain = Literal[
    "coding", "math", "reasoning", "knowledge", "agentic", "long_context", "writing", "multilingual", "general"
]
RouterLatency = Literal["interactive", "standard", "batch"]
Difficulty = Literal["easy", "medium", "hard"]

RunState = Literal["pending", "running", "completed", "failed"]


class RunEvent(BaseModel):
    """One SSE frame. ``event`` is ``state`` or ``terminal``; a terminal frame
    carries ``kind`` plus ``verdict`` or ``decision``."""

    event: str
    run_id: Optional[str] = None
    state: Optional[RunState] = None
    input_digest: Optional[str] = None
    output_digest: Optional[str] = None
    kind: Optional[Literal["verdict", "decision"]] = None
    verdict: Optional[Any] = None
    decision: Optional[Any] = None

    @property
    def is_terminal(self) -> bool:
        return self.event == "terminal"


__all__ = [  # noqa: F405
    "Difficulty",
    "RouterBenchmarkContribution",
    "RouterBenchmarkHighlight",
    "RouterCatalog",
    "RouterCatalogModel",
    "RouterClassification",
    "RouterDomain",
    "RouterFacets",
    "RouterFilterCount",
    "RouterImputed",
    "RouterLabel",
    "RouterLatency",
    "RouterModel",
    "RouterModelFilters",
    "RouterModelRef",
    "RouterModelsResponse",
    "RouterPolicy",
    "RouterRankingEntry",
    "RouterScores",
    "RouterSelectRequest",
    "RouterSelectResponse",
    "RouterTaskType",
    "RouterTaskTypeInfo",
    "RouterTaskTypeProbability",
    "RouterTaskTypesResponse",
    "RouterTaskWeight",
    "RouterThreshold",
    "RouterWeights",
    "RunEvent",
    "RunResponse",
    "RunState",
]
