"""Contract tests for the LOCAL_MVP agentic adapter."""
from __future__ import annotations

from typing import Any

import pytest

from criba.agentic import LocalAgenticLayer, get_layer


class FakeEngine:
    """Deterministic engine double with the production activate signature."""

    def __init__(self, packet: dict[str, Any]) -> None:
        self.packet = packet
        self.calls: list[dict[str, Any]] = []

    def activate(
        self,
        query: str,
        current: str = "auto",
        mode: str = "balanced",
        supporting_methods: int = 4,
        context: dict[str, Any] | None = None,
        safety_level: str = "strict",
        manual_methods: list[str] | None = None,
    ) -> dict[str, Any]:
        self.calls.append({
            "query": query,
            "current": current,
            "mode": mode,
            "supporting_methods": supporting_methods,
            "safety_level": safety_level,
        })
        return self.packet


def test_local_layer_returns_engine_ideas_and_forwards_options() -> None:
    ideas = [{"id": "IDEA-001", "title": "Prueba"}]
    engine = FakeEngine({"innovation": {"ideas": ideas}})

    result = LocalAgenticLayer(engine).generate_ideas({
        "query": "problema",
        "current": "causal_contrafactual",
        "mode": "strict",
        "supporting_methods": 3,
        "safety_level": "standard",
    })

    assert result == ideas
    assert engine.calls == [{
        "query": "problema",
        "current": "causal_contrafactual",
        "mode": "strict",
        "supporting_methods": 3,
        "safety_level": "standard",
    }]


@pytest.mark.parametrize("packet", [
    {},
    {"innovation": None},
    {"innovation": {"ideas": "not-a-list"}},
    {"innovation": {"ideas": ["not-a-mapping"]}},
])
def test_local_layer_rejects_malformed_engine_packets(packet: dict[str, Any]) -> None:
    with pytest.raises(TypeError, match="innovation"):
        LocalAgenticLayer(FakeEngine(packet)).generate_ideas({"query": "problema"})


def test_local_novelty_hook_is_explicitly_not_implemented() -> None:
    engine = FakeEngine({"innovation": {"ideas": []}})
    result = LocalAgenticLayer(engine).evaluate_novelty([])
    assert result["status"] == "not_implemented_yet"
    assert result["mode"] == "LOCAL_MVP"


def test_factory_rejects_unavailable_and_unknown_modes() -> None:
    engine = FakeEngine({"innovation": {"ideas": []}})
    assert isinstance(get_layer("LOCAL_MVP", engine), LocalAgenticLayer)
    with pytest.raises(NotImplementedError, match="future hook"):
        get_layer("AGENTIC", engine)
    with pytest.raises(ValueError, match="desconocido"):
        get_layer("INVALID", engine)
