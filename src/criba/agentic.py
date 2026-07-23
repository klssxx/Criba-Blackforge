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
from typing import Dict, List, Protocol


class AgenticLayer(Protocol):
    """Contract for idea generation + novelty evaluation.

    LOCAL_MVP implements this with the deterministic engine. AGENTIC (future)
    would implement it with multi-agent + RAG + external evaluators.
    """
    mode: str

    def generate_ideas(self, base_context: Dict) -> List[Dict]:
        ...

    def evaluate_novelty(self, ideas: List[Dict]) -> Dict:
        ...


class LocalAgenticLayer:
    """LOCAL_MVP stub: delegates to the deterministic engine. No network, no
    external evaluation. This is the ONLY implementation active in the MVP."""
    mode = "LOCAL_MVP"

    def __init__(self, engine_module):
        self._engine = engine_module

    def generate_ideas(self, base_context: Dict) -> List[Dict]:
        packet = self._engine.activate(
            base_context["query"],
            current=base_context.get("current", "auto"),
            mode=base_context.get("mode", "balanced"),
            supporting_methods=base_context.get("supporting_methods", 4),
            safety_level=base_context.get("safety_level", "strict"),
        )
        return packet["innovation"]["ideas"]

    def evaluate_novelty(self, ideas: List[Dict]) -> Dict:
        # Not implemented in LOCAL_MVP: novelty is measured by causal-axis
        # divergence + CCA inside the engine, not by an external evaluator.
        return {"status": "not_implemented_yet", "mode": self.mode,
                "note": "external novelty evaluator (SPARK-like) is a future AGENTIC hook"}


def get_layer(mode: str, engine_module):
    """Factory. Only LOCAL_MVP is wired today; AGENTIC is a future hook."""
    if mode == "LOCAL_MVP":
        return LocalAgenticLayer(engine_module)
    if mode == "AGENTIC":
        raise NotImplementedError(
            "AGENTIC layer (multi-agent + RAG + external novelty evaluator) is a "
            "future hook, not implemented in the MVP. Hy3 is already the LLM backend; "
            "this flag would enable the agentic ARCHITECTURE on top of it.")
    raise ValueError(f"modo de capa agentic desconocido: {mode}")
