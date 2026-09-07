"""Tests del router de técnicas sobre el canon T001-T130.

Determinista y offline por construcción: el router solo lee metadata del
registro (sin modelo, sin red, sin ejecución).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from criba.intelligence.registry import TechniqueRegistry
from criba.intelligence.router import TechniqueRouter

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "data" / "intelligence" / "technique_registry.yaml"


@pytest.fixture(scope="module")
def router() -> TechniqueRouter:
    return TechniqueRouter(TechniqueRegistry(REGISTRY_PATH))


def test_selection_is_deterministic(router: TechniqueRouter) -> None:
    """Misma tarea → mismo resultado, dos veces (sin azar en el routing)."""
    task = "búsqueda de patentes sobre un mecanismo de cierre"
    first = router.select(task)
    second = router.select(task)
    assert first.to_dict() == second.to_dict()


def test_selected_contains_only_implemented(router: TechniqueRouter) -> None:
    """Solo técnicas IMPLEMENTED son candidatos de ejecución."""
    result = router.select("análisis morfológico y scamper de un problema")
    assert result.selected, "la tarea debe activar al menos una técnica implementada"
    for candidate in result.selected:
        assert candidate.executable
        assert candidate.technique.status.startswith("IMPLEMENTED")


def test_planned_never_claimed_as_capability(router: TechniqueRouter) -> None:
    """Las PLANNED relevantes aparecen solo como brechas, nunca ejecutables."""
    result = router.select("genealogía de innovación y curvas de sustitución")
    assert result.coverage_gaps, "T130 (PLANNED) debe aparecer como brecha"
    for candidate in result.coverage_gaps:
        assert not candidate.executable
        assert candidate.technique.status == "PLANNED"
    for candidate in result.selected:
        assert candidate.technique.status.startswith("IMPLEMENTED")


def test_irrelevant_task_yields_empty_selection(router: TechniqueRouter) -> None:
    """Sin coincidencia real no se inventa relevancia: selección vacía."""
    result = router.select("zzz qqq xyzzy")
    assert result.selected == ()
    assert result.coverage_gaps == ()


def test_max_techniques_respected(router: TechniqueRouter) -> None:
    result = router.select("patentes, tendencias, señales y adversarios", max_techniques=2)
    assert len(result.selected) <= 2


def test_family_diversity_cap(router: TechniqueRouter) -> None:
    """No colapsar en una sola familia cuando hay relevancia comparable."""
    result = router.select(
        "análisis morfológico y escenarios contrafactuales",
        max_techniques=6, max_per_family=1,
    )
    families = [c.technique.family for c in result.selected]
    assert len(families) == len(set(families))
    assert len(families) >= 2, "dos familias relevantes no deben colapsar en una"


def test_blackforge_profile_changes_weighting(router: TechniqueRouter) -> None:
    """El perfil BLACKFORGE reordena hacia familias adversariales/señales."""
    task = "evaluar señales y escenarios adversariales de un problema"
    criba = router.select(task, profile="CRIBA")
    blackforge = router.select(task, profile="BLACKFORGE")
    assert criba.to_dict() != blackforge.to_dict()
    adversarial = [
        c.id for c in (*blackforge.selected, *blackforge.coverage_gaps)
        if c.technique.family == "ADVERSARIAL_FUTURES"
    ]
    assert adversarial, "BLACKFORGE debe surfaced técnicas adversariales relevantes"


def test_unknown_profile_rejected(router: TechniqueRouter) -> None:
    with pytest.raises(ValueError):
        router.select("tarea", profile="INVENTADO")


def test_result_carries_traceability(router: TechniqueRouter) -> None:
    """El resultado arrastra versión + procedencia del canon consumido."""
    result = router.select("inversión de restricciones")
    assert result.canon_version, "canon_version del registro debe viajar"
    assert result.provenance.get("generator", "").endswith("gen_registry.py")
    assert len(result.provenance["parts"]) == 4
    as_dict = result.to_dict()
    assert as_dict["canon_version"] == result.canon_version
    assert as_dict["provenance"] == dict(result.provenance)


def test_offline_only_excludes_network_techniques(router: TechniqueRouter) -> None:
    """offline_only=True (defecto) excluye técnicas con red y lo deja anotado."""
    result = router.select("buscar en patentes y publicaciones científicas")
    network_selected = [c for c in result.selected if c.technique.requires_network]
    assert network_selected == []
    # anotación honesta de lo excluido por la política offline
    assert any("requiere_red" in e for e in result.excluded)


def test_morphological_task_selects_t059(router: TechniqueRouter) -> None:
    """Caso funcional: una tarea morfológica encuentra T059 (implementada)."""
    result = router.select("generar hipótesis con análisis morfológico de dimensiones")
    assert "T059" in [c.id for c in result.selected]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
