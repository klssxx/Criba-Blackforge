"""§82: cadena real canon → TechniqueRegistry → TechniqueRouter → resolver
→ operador restaurado → salida contractual válida.

La existencia de un módulo no promociona una técnica (§80); una técnica
IMPLEMENTED debe ser ejecutable de verdad a través de la cadena canónica.
Negativos: PLANNED nunca ejecutable; IMPLEMENTED con referencia rota o sin
test real → el guard falla (el router no puede fabricar disponibilidad).
"""
from __future__ import annotations

import importlib
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from criba.intelligence.contracts import EvidenceDocument, InventionCandidate
from criba.intelligence.registry import TechniqueRegistry
from criba.intelligence.router import TechniqueRouter

from tests.intelligence.test_technique_runtime_traceability import (
    _expand_implementation,
    _ref_resolves,
    _test_function_names,
)

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "data" / "intelligence" / "technique_registry.yaml"


def _evidence(**metadata: Any) -> EvidenceDocument:
    return EvidenceDocument(title="doc sintético", metadata=dict(metadata))


def _resolve_callable(dotted: str) -> Callable[..., Any]:
    """Execution resolver: 'pkg.mod.func' → objeto vivo (falla si está roto)."""
    parts = dotted.split(".")
    assert _ref_resolves(parts), f"referencia no resoluble: {dotted}"
    module = importlib.import_module(".".join(parts[:-1]))
    obj = getattr(module, parts[-1])
    assert callable(obj), f"no es ejecutable: {dotted}"
    return obj


# Operador principal por técnica + entrada mínima contractual (input_contracts
# del canon). T057: el primario es list_principles (get_principle pide número).
_PRIMARY_OPERATOR: dict[str, tuple[str, Callable[[], tuple[Any, ...]]]] = {
    "T053": ("criba.intelligence.invention.rare_combinations.detect_rare_combinations",
             lambda: ([_evidence(concepts=["a", "b"]), _evidence(concepts=["b", "c"]),
                       _evidence(concepts=["a", "b"]), _evidence(concepts=["c", "d"])],)),
    "T055": ("criba.intelligence.invention.cross_domain.detect_cross_domain_analogies",
             lambda: ([_evidence(domain="quimica", concepts=["membrana", "transporte"]),
                       _evidence(domain="logistica", concepts=["membrana", "ruta"])],)),
    "T057": ("criba.intelligence.invention.triz.list_principles", lambda: ()),
    "T059": ("criba.intelligence.invention.morphology.generate_morphological_hypotheses",
             lambda: ("problema", {"dimension_a": ["x", "y"], "dimension_b": ["1", "2"]})),
    "T060": ("criba.intelligence.invention.scamper.generate_scamper_hypotheses",
             lambda: ("problema", ["componente_a", "componente_b"])),
    "T062": ("criba.intelligence.invention.functions.decompose_functional_hypotheses",
             lambda: ("problema", {"componente": ["funcion_1", "funcion_2"]})),
    "T063": ("criba.intelligence.invention.functions.search_function_to_mechanism_hypotheses",
             lambda: ("problema", ["funcion_1"],
                      [_evidence(function_mechanisms={"funcion_1": ["mecanismo_x"]})])),
    "T064": ("criba.intelligence.invention.first_principles.decompose_first_principles_hypotheses",
             lambda: ("problema", {"premisa": ["implicacion_1", "implicacion_2"]})),
    "T065": ("criba.intelligence.invention.inversion.generate_constraint_inversion_hypotheses",
             lambda: ("problema", {"restriccion": ["inversion_1", "inversion_2"]})),
    "T116": ("criba.intelligence.invention.adjacent_possible.generate_adjacent_possible_hypotheses",
             lambda: (("problema", ["cap_a", "cap_b", "cap_c"]),
                      {"known_combinations": [["cap_a", "cap_b"]]})),
    "T129": ("criba.intelligence.invention.counterfactual.generate_counterfactual_hypotheses",
             lambda: ("problema", {"futuro": ["estado_a", "estado_b"]})),
}


@pytest.mark.parametrize("tid", sorted(_PRIMARY_OPERATOR))
def test_chain_canon_to_operator_output(tid: str) -> None:
    """CANON→Registry→Router→resolver→operador→salida contractual (§82)."""
    registry = TechniqueRegistry(REGISTRY_PATH)
    technique = registry.get(tid)
    assert technique.status.startswith("IMPLEMENTED"), f"{tid} debe estar promocionada"

    # 1) Router: la IMPLEMENTED se ofrece como ejecutable ante tarea pertinente
    #    (permitir red si la técnica canónica la declara: el router offline la
    #    excluye por política, no por capacidad).
    router = TechniqueRouter(registry)
    result = router.select(
        technique.name, max_techniques=30, max_per_family=30,
        offline_only=not technique.requires_network,
    )
    offered = {c.technique.id: c.executable for c in result.selected}
    assert offered.get(tid) is True, f"{tid}: IMPLEMENTED no ofrecida como ejecutable"

    # 2) Todas las referencias del canon resuelven (resolver vivo).
    for ref in _expand_implementation(technique.implementation or ""):
        assert _ref_resolves(ref.split(".")), f"{tid}: ref rota {ref}"

    # 3) El operador principal ejecuta con entrada contractual y produce salida.
    #    Forma de la factoría: (args...) o ((args...), {kwargs}) anidada.
    operator_ref, args_factory = _PRIMARY_OPERATOR[tid]
    call_args = args_factory()
    if (len(call_args) == 2 and isinstance(call_args[0], tuple)
            and isinstance(call_args[1], dict)):
        call_args, call_kwargs = call_args
    else:
        call_kwargs = {}
    output = _resolve_callable(operator_ref)(*call_args, **call_kwargs)
    assert output, f"{tid}: sin salida con entrada contractual mínima"

    # 4) Salida contractual: candidatos con trazabilidad de operador (o el
    #    catálogo TRIZ para T057).
    if tid == "T057":
        names = [p.name if hasattr(p, "name") else str(p) for p in output]
        assert len(names) == 40
    else:
        for candidate in output:
            assert isinstance(candidate, InventionCandidate)
            assert tid in candidate.operators, f"{tid}: candidato sin trazabilidad"


def test_planned_never_offered_as_executable() -> None:
    """Negativo §82: ninguna técnica PLANNED del canon real es ejecutable."""
    registry = TechniqueRegistry(REGISTRY_PATH)
    router = TechniqueRouter(registry)
    planned_ids = {t.id for t in registry.all() if t.status == "PLANNED"}
    probe = " ".join(
        t.name for t in registry.all()
        if t.family in ("SIGNALS_EVIDENCE_OPPORTUNITY", "ADVERSARIAL_FUTURES")
    )
    result = router.select(probe, max_techniques=50, max_per_family=50)
    seen_planned = 0
    for candidate in (*result.selected, *result.coverage_gaps):
        if candidate.technique.id in planned_ids:
            seen_planned += 1
            assert not candidate.executable
            assert candidate.technique.status == "PLANNED"
    assert seen_planned > 0, "la sonda debe alcanzar técnicas PLANNED para que el negativo pruebe algo"


def test_guard_fails_on_broken_reference_and_missing_test() -> None:
    """Negativo §82: IMPLEMENTED con referencia rota o test declarado
    inexistente no puede pasar el guard de trazabilidad runtime."""
    broken = "criba.intelligence.invention.modulo_que_no_existe.funcion"
    assert not _ref_resolves(broken.split(".")), "referencia rota no debe resolver"
    real_names = _test_function_names()
    assert "test_que_no_existe_en_ningun_sitio" not in real_names
    # guard en verde sobre el canon real: IMPLEMENTED resuelven y declaran reales.
    registry = TechniqueRegistry(REGISTRY_PATH)
    for technique in registry.implemented():
        for ref in _expand_implementation(technique.implementation or ""):
            assert _ref_resolves(ref.split("."))
        for declared in technique.tests:
            assert declared in real_names


def test_dispatch_registry_enforces_contract_not_authority() -> None:
    """§78: invention.registry es dispatch + validación contractual; no es
    canon paralelo (la definición referencia Txxx, no redefine status)."""
    from criba.intelligence.invention.morphology import generate_morphological_hypotheses
    from criba.intelligence.invention.registry import OperatorContext, OperatorRegistry
    from criba.intelligence.invention.taxonomy import OPERATORS_BY_KEY

    # la definición es dispatch: mapea key→módulo/Txxx; no lleva status.
    definition = OPERATORS_BY_KEY["morphological_analysis"]
    assert definition.technique_ids == ("T059",)
    assert not hasattr(definition, "status")

    operators = OperatorRegistry()
    operators.register("morphological_analysis", lambda ctx: generate_morphological_hypotheses(
        ctx.problem, {"dim": ["a", "b"]}))

    output = operators.execute(
        "morphological_analysis",
        OperatorContext(problem="problema", evidence_doc_ids=("doc-1",)),
    )
    assert output and all(isinstance(c, InventionCandidate) for c in output)
    assert all("T059" in c.operators for c in output)

    with pytest.raises(LookupError):  # definición sin handler NO ejecuta
        operators.execute("scamper", OperatorContext(problem="p"))
    operators.register("scamper", lambda ctx: [InventionCandidate(title="x")])
    with pytest.raises(ValueError, match="technique traceability"):  # contrato
        operators.execute("scamper", OperatorContext(problem="p"))


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))


# ---------------------------------------------------------------------------
# Slice 2 (canon 2026-09-08.2): gaps/signals restaurados + ejecutables.
# Misma cadena §82, adaptadores por input_contracts, guardrails de canon.
# ---------------------------------------------------------------------------

def _series(topic: str = "ia") -> list[dict]:
    return [
        {"topic": topic, "period": "2026-01", "frequency": 5},
        {"topic": topic, "period": "2026-02", "frequency": 20},
        {"topic": topic, "period": "2026-03", "frequency": 22},
    ]


def _doc(abstract: str = "The method fails when load doubles") -> EvidenceDocument:
    return EvidenceDocument(title="doc sintético", abstract=abstract)


SLICE2_CASES = {
    "T067": {"documents": [_doc()], "expect_type": None},
    "T068": {"documents": [_doc()], "expect_type": None},
    "T069": {"documents": [_doc()], "expect_type": None},
    "T070": {"documents": [_doc()], "expect_type": None},
    "T071": {"documents": [_doc()], "expect_type": None},
    "T086": {"documents": [_doc()], "expect_type": None},
    "T128": {"documents": [_doc()], "expect_type": None},
    "T019": {"params": {"observations": _series(), "topic": "ia"}},
    "T048": {"params": {"observations": _series(), "topic": "ia"}},
    "T049": {"params": {"observations": _series(), "topic": "ia"}},
    "T096": {"params": {"observations": _series()}},
    "T097": {"params": {"observations": _series()}},
    "T098": {"params": {"observations": _series()}},
    "T099": {"params": {"signals": [{"signal_id": "s1", "kind": "anomaly", "topic": "ia",
                                     "strength": 0.8, "direction": "up"}]}},
    "T101": {"params": {"observations": _series() + _series("seguidor"),
                        "leader_topic": "ia", "follower_topic": "seguidor"}},
}


@pytest.mark.parametrize("tid", sorted(SLICE2_CASES))
def test_chain_slice2_execute(tid: str) -> None:
    """Canon 2026-09-08.2 → execute_technique → salida con forma contractual."""
    from criba.intelligence.execution import execute_technique

    registry = TechniqueRegistry(REGISTRY_PATH)
    case = SLICE2_CASES[tid]
    technique = registry.get(tid)
    assert technique.status.startswith("IMPLEMENTED")

    outcome = execute_technique(
        registry, tid, "problema",
        params=case.get("params"), documents=case.get("documents"),
    )
    assert outcome["technique"] == tid
    assert outcome["canon_version"]
    assert isinstance(outcome["results"], list)


def test_slice2_guardrails_still_enforced() -> None:
    """Negativo: las nuevas también respetan la autoridad del canon."""
    from criba.intelligence.execution import ExecutionError, execute_technique

    registry = TechniqueRegistry(REGISTRY_PATH)
    with pytest.raises(ExecutionError, match="PLANNED"):
        execute_technique(registry, "T052", "p", params={"observations": _series()})
    with pytest.raises(ExecutionError, match="desconocida"):
        execute_technique(registry, "T000", "p")
    # input_contracts honrados: dynamics sin topic → error honrado
    with pytest.raises(ExecutionError, match="topic"):
        execute_technique(registry, "T048", "p", params={"observations": _series()})
