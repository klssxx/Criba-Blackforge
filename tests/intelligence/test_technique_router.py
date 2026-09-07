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
    """El canon real no tiene hoy ninguna técnica IMPLEMENTED (cbac469 eliminó
    invention/*): nada es ejecutable y todo relevante sale como brecha."""
    result = router.select("análisis morfológico y scamper de un problema")
    assert result.selected == ()
    assert result.coverage_gaps, "las técnicas relevantes deben aparecer como brechas"
    for candidate in result.selected:  # invariante: si hubiese seleccionadas, ejecutables
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


def test_family_diversity_cap(tmp_path) -> None:
    """No colapsar en una sola familia cuando hay relevancia comparable
    (canon sintético con técnicas ejecutables en dos familias)."""
    implemented_a = _entry(
        id="T910", name="morphological analysis engine", family="INVENTION",
        module=["criba.intelligence.prior_art.mutation_loop"],
        implementation="criba.intelligence.prior_art.mutation_loop.run_prior_art_mutation_loop",
    )
    implemented_b = _entry(
        id="T920", name="counterfactual scenario mapping", family="ADVERSARIAL_FUTURES",
        module=["criba.intelligence.prior_art.verdict"],
        implementation="criba.intelligence.prior_art.verdict",
    )
    registry = _synthetic_registry(tmp_path, [implemented_a, implemented_b])
    result = TechniqueRouter(registry).select(
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
    """Caso funcional: una tarea morfológica encuentra T059. Desde la cirugía
    cbac469 el módulo no existe → T059 es PLANNED y sale como brecha honesta,
    nunca como ejecutable."""
    result = router.select("generar hipótesis con análisis morfológico de dimensiones")
    t059 = [c for c in result.coverage_gaps if c.id == "T059"]
    assert t059, "T059 debe aparecer como brecha"
    assert not t059[0].executable
    assert t059[0].technique.status == "PLANNED"


def test_executable_path_with_synthetic_registry(tmp_path) -> None:
    """La vía ejecutable sigue probada: una IMPLEMENTED con código real se
    selecciona (executable=True, bonus aplicado) y la PLANNED gemela queda
    como brecha en el mismo barrido."""
    implemented = _entry(
        id="T910", name="prior art mutation loop engine",
        family="INVENTION",
        module=["criba.intelligence.prior_art.mutation_loop"],
        implementation="criba.intelligence.prior_art.mutation_loop.run_prior_art_mutation_loop",
    )
    planned = _entry(
        id="T911", name="prior art mutation loop future variant",
        family="INVENTION", status="PLANNED", implementation=None,
        input_contracts=[], output_contracts=[],
    )
    registry = _synthetic_registry(tmp_path, [implemented, planned])
    result = TechniqueRouter(registry).select("prior art mutation loop engine")
    selected_ids = [c.id for c in result.selected]
    gap_ids = [c.id for c in result.coverage_gaps]
    assert "T910" in selected_ids
    t910 = result.selected[selected_ids.index("T910")]
    assert t910.executable and t910.technique.status == "IMPLEMENTED"
    assert "T911" in gap_ids, "la gemela PLANNED debe salir como brecha"


# -- qa P3-1/P3-2/P3-3 ---------------------------------------------------------

def _synthetic_registry(tmp_path, techniques):
    """Registro v2 sintético (cabecera completa) para casos que el canon real
    no puede representar (p. ej. requires_credentials=true)."""
    import yaml as _yaml

    raw = {
        "schema_version": 2,
        "canon_version": "synthetic.1",
        "provenance": {"source": "test", "generator": "test", "parts": ["p1"]},
        "techniques": techniques,
    }
    p = tmp_path / "synthetic_registry.yaml"
    p.write_text(_yaml.safe_dump(raw), encoding="utf-8")
    return TechniqueRegistry(p)


def _entry(**overrides):
    base = {
        "id": "T900", "name": "base", "family": "INVENTION",
        "owner": "CRIBA_IIE", "module": ["criba.intelligence.invention"],
        "phase": ["P01"], "pipelines": ["INVENTION"],
        "status": "IMPLEMENTED", "implementation": "criba.test",
        "input_contracts": ["x"], "output_contracts": ["y"], "tests": ["t"],
    }
    base.update(overrides)
    return base


def test_reasons_truncate_on_token_boundary(tmp_path) -> None:
    """qa P3-1: con muchos tokens coincidentes el reason nunca corta un token
    a la mitad ni deja coma colgante; los tokens omitidos desaparecen enteros."""
    from criba.intelligence.router import TechniqueRouter as TR, _tokens

    words = ["arboleda", "barquito", "carabela", "domino", "espejismo", "frase",
             "gatito", "hormigon", "iceberg", "jirafa", "koala", "lampara"]
    long_name = " ".join(words)
    registry = _synthetic_registry(tmp_path, [_entry(name=long_name)])
    router = TR(registry)
    task = long_name  # los 12 tokens coinciden: el join completo supera 80
    result = router.select(task)

    matched = _tokens(task)
    full = ",".join(sorted(matched))
    assert len(full) > 80, "el doc sintético debe forzar el truncado"
    reasons = [r for c in (*result.selected, *result.coverage_gaps)
               for r in c.reasons if r.startswith("coincide:")]
    assert reasons
    for reason in reasons:
        inner = reason[len("coincide:"):]
        assert len(inner) <= 80, "el reason debe seguir acotado"
        assert not inner.endswith(","), "sin coma colgante"
        # prefijo del join completo terminando en frontera de token:
        assert full.startswith(inner)
        assert full[len(inner):len(inner) + 1] in ("", ",")
        listed = inner.split(",")
        assert set(listed) <= matched, "ningún token parcial inventado"


def test_invalid_limits_rejected(router: TechniqueRouter) -> None:
    """qa P3-2: max/max_per_family < 1 son error del llamador, no selección vacía."""
    with pytest.raises(ValueError, match="max_techniques"):
        router.select("morfologico", max_techniques=0)
    with pytest.raises(ValueError, match="max_techniques"):
        router.select("morfologico", max_techniques=-1)
    with pytest.raises(ValueError, match="max_per_family"):
        router.select("morfologico", max_per_family=0)
    with pytest.raises(ValueError, match="max_per_family"):
        router.select("morfologico", max_per_family=-1)


def test_credentials_gate_excludes_even_with_network_allowed(tmp_path) -> None:
    """qa P3-3: requiere_credenciales excluye la técnica (nunca selected ni
    coverage_gaps) incluso con offline_only=False; la técnica gemela sin
    credenciales sí es seleccionable, demostrando que el gate discrimina."""
    cred = _entry(
        id="T900", name="credentialed portal search", requires_credentials=True,
        requires_network=False,
    )
    free = _entry(
        id="T901", name="local manual search", requires_credentials=False,
        requires_network=False,
    )
    router = TechniqueRouter(_synthetic_registry(tmp_path, [cred, free]))
    task = "portal search manual"

    for offline_only in (False, True):
        result = router.select(task, offline_only=offline_only)
        ids_selected = [c.id for c in result.selected]
        ids_gaps = [c.id for c in result.coverage_gaps]
        assert "T900" not in ids_selected
        assert "T900" not in ids_gaps
        assert "T900:requiere_credenciales" in result.excluded
        assert "T901" in ids_selected, "la gemela sin credenciales sí pasa"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
