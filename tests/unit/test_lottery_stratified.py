"""Tests del sorteo estratificado por clases de pensamiento (catálogo estructurado)."""
from __future__ import annotations

import pytest

from criba.lottery import DOMAIN_CLASS, DRAW_CLASSES, LotteryEngine


def _synthetic_catalog(per_class: int = 50, domain: int = 30) -> list[dict]:
    catalog: list[dict] = []
    for class_name in DRAW_CLASSES:
        for i in range(per_class):
            catalog.append(
                {
                    "id": f"{class_name}-{i:03d}",
                    "name": f"{class_name}-{i:03d}",
                    "title": f"{class_name} {i:03d}",
                    "family": class_name,
                    "thinking_class": class_name,
                }
            )
    for i in range(domain):
        catalog.append(
            {
                "id": f"dominio-{i:03d}",
                "name": f"dominio-{i:03d}",
                "title": f"Metodología de dominio {i:03d}",
                "family": "metodologias",
                "thinking_class": DOMAIN_CLASS,
            }
        )
    return catalog


def test_stratified_batch_distributes_classes_equally() -> None:
    engine = LotteryEngine.from_methods(_synthetic_catalog(), seed=42)
    batch = engine.select_stratified_batch(40)
    assert len(batch) == 40
    counts: dict[str, int] = {}
    for method in batch:
        counts[str(method["thinking_class"])] = counts.get(str(method["thinking_class"]), 0) + 1
    for class_name in DRAW_CLASSES:
        assert counts.get(class_name, 0) == 10


def test_stratified_batch_excludes_domain_bank() -> None:
    engine = LotteryEngine.from_methods(_synthetic_catalog(), seed=1)
    batch = engine.select_stratified_batch(24)
    assert all(m["thinking_class"] != DOMAIN_CLASS for m in batch)


def test_stratified_batch_is_deterministic_per_seed() -> None:
    ids_a = [m["id"] for m in LotteryEngine.from_methods(_synthetic_catalog(), seed=7).select_stratified_batch(20)]
    ids_b = [m["id"] for m in LotteryEngine.from_methods(_synthetic_catalog(), seed=7).select_stratified_batch(20)]
    assert ids_a == ids_b


def test_stratified_batch_different_seeds_differ() -> None:
    ids_a = [m["id"] for m in LotteryEngine.from_methods(_synthetic_catalog(), seed=1).select_stratified_batch(20)]
    ids_b = [m["id"] for m in LotteryEngine.from_methods(_synthetic_catalog(), seed=2).select_stratified_batch(20)]
    assert ids_a != ids_b


def test_draw_domain_returns_domain_entry() -> None:
    engine = LotteryEngine.from_methods(_synthetic_catalog(), seed=3)
    drawn = engine.draw_domain()
    assert drawn is not None
    assert drawn["thinking_class"] == DOMAIN_CLASS


def test_stratified_falls_back_without_classes() -> None:
    legacy = [
        {"id": f"bf-{i:03d}", "name": f"bf-{i:03d}", "title": f"BF {i}", "family": "blackforge"}
        for i in range(10)
    ]
    engine = LotteryEngine.from_methods(legacy, seed=5)
    batch = engine.select_stratified_batch(6)
    assert len(batch) == 6


def test_run_round_accepts_stratified_mode_and_tracks_classes() -> None:
    engine = LotteryEngine.from_methods(_synthetic_catalog(), seed=11)
    stats = engine.run_round(mode="stratified", batch_size=8)
    assert stats["mode"] == "stratified"
    assert set(stats["classes"]).issubset(set(DRAW_CLASSES))
    assert engine.all_ideas, "la ronda estratificada debe generar ideas"
    for idea in engine.all_ideas:
        assert "class1" in idea and "class2" in idea


def test_invalid_size_rejected() -> None:
    engine = LotteryEngine.from_methods(_synthetic_catalog(), seed=1)
    with pytest.raises(ValueError):
        engine.select_stratified_batch(0)
