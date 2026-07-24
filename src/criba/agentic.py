"""Agentic layer boundary (architecture, not the LLM).

Two distinct things were being confused in the roadmap:

- ``llm_backend = "hy3"``  -> the Tencent Hy3 MoE model already in use by Hermes
  for generation. This is the MODEL, in use today.
- ``mode = "LOCAL_MVP"`` vs ``mode = "AGENTIC"`` -> the system architecture stage.

LOCAL_MVP (today): offline, deterministic, 5-dim causal genome, family crossover,
forced divergence. Hy3 is used ONLY as the generation engine, not as orchestrator
or external evaluator.

AGENTIC (future hook): multi-agent orchestration, external RAG/search, dedicated
novelty evaluators (SPARK/LiveIdeaBench-like). Hy3 is one worker among others.

This module defines the contract so the future AGENTIC layer plugs in without
rewriting the engine. Today only ``LocalAgenticLayer`` exists (a stub).
"""
from __future__ import annotations

from typing import Any, Mapping, Protocol, cast

JsonDict = dict[str, Any]


class EngineModule(Protocol):
    """Minimum engine interface consumed by the local agentic adapter."""

    def activate(
        self,
        query: str,
        current: str = "auto",
        mode: str = "balanced",
        supporting_methods: int = 4,
        context: dict[str, Any] | None = None,
        safety_level: str = "strict",
        manual_methods: list[str] | None = None,
    ) -> JsonDict:
        ...


class AgenticLayer(Protocol):
    """Contract for idea generation + novelty evaluation.

    LOCAL_MVP implements this with the deterministic engine. AGENTIC (future)
    would implement it with multi-agent + RAG + external evaluators.
    """

    mode: str

    def generate_ideas(self, base_context: Mapping[str, Any]) -> list[JsonDict]:
        ...

    def evaluate_novelty(self, ideas: list[JsonDict]) -> JsonDict:
        ...


class LocalAgenticLayer:
    """LOCAL_MVP adapter for the deterministic engine.

    It performs no network access and no external evaluation. This is the only
    implementation active in the MVP.
    """

    mode = "LOCAL_MVP"

    def __init__(self, engine_module: EngineModule) -> None:
        self._engine = engine_module

    def generate_ideas(self, base_context: Mapping[str, Any]) -> list[JsonDict]:
        packet = self._engine.activate(
            base_context["query"],
            current=base_context.get("current", "auto"),
            mode=base_context.get("mode", "balanced"),
            supporting_methods=base_context.get("supporting_methods", 4),
            safety_level=base_context.get("safety_level", "strict"),
        )
        innovation = packet.get("innovation")
        if not isinstance(innovation, Mapping):
            raise TypeError("engine packet field 'innovation' must be a mapping")
        ideas = innovation.get("ideas")
        if not isinstance(ideas, list) or not all(isinstance(item, dict) for item in ideas):
            raise TypeError("engine packet field 'innovation.ideas' must be a list of mappings")
        return cast(list[JsonDict], ideas)

    def evaluate_novelty(self, ideas: list[JsonDict]) -> JsonDict:
        # Not implemented in LOCAL_MVP: novelty is measured by causal-axis
        # divergence + CCA inside the engine, not by an external evaluator.
        return {
            "status": "not_implemented_yet",
            "mode": self.mode,
            "note": "external novelty evaluator (SPARK-like) is a future AGENTIC hook",
        }


def get_layer(mode: str, engine_module: EngineModule) -> AgenticLayer:
    """Return the configured layer; only LOCAL_MVP is currently available."""
    if mode == "LOCAL_MVP":
        return LocalAgenticLayer(engine_module)
    if mode == "AGENTIC":
        raise NotImplementedError(
            "AGENTIC layer (multi-agent + RAG + external novelty evaluator) is a "
            "future hook, not implemented in the MVP. Hy3 is already the LLM backend; "
            "this flag would enable the agentic ARCHITECTURE on top of it."
        )
    raise ValueError(f"modo de capa agentic desconocido: {mode}")
