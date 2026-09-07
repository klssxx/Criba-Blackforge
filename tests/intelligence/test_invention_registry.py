"""§77/§78/§79: coherencia dispatch↔canon con UNA autoridad.

El canon (TechniqueRegistry) decide status; la tabla de operadores es
dispatch. Este test verifica la reconciliación en AMBAS direcciones para
que ninguna de las dos fuentes derive en autoridad paralela: todo operador
declarado con módulo real debe estar IMPLEMENTED en el canon (ejecutar sin
autoridad canónica es un defecto), y el canon no declara IMPLEMENTED nada
sin operador con módulo real (falsa capacidad)."""

from __future__ import annotations

from pathlib import Path

from criba.intelligence.invention import get_operator
from criba.intelligence.registry import TechniqueRegistry

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "data" / "intelligence" / "technique_registry.yaml"
IMPLEMENTED_OPERATOR_KEYS = (
    "rare_combinations",
    "cross_domain_analogy",
    "triz",
    "morphological_analysis",
    "scamper",
    "functional_decomposition",
    "function_to_mechanism",
    "first_principles",
    "constraint_inversion",
    "adjacent_possible",
    "counterfactual",
    "future_back",
    "bottleneck_mapping",
    "nth_order",
)
EXPECTED_TECHNIQUE_IDS = {
    "T053",
    "T055",
    "T057",
    "T059",
    "T060",
    "T062",
    "T063",
    "T064",
    "T065",
    "T116",
    "T129",
}


def test_implemented_invention_operators_match_registry_contracts():
    registry = TechniqueRegistry(REGISTRY_PATH)
    resolved_ids: set[str] = set()

    for key in IMPLEMENTED_OPERATOR_KEYS:
        definition = get_operator(key)
        assert definition is not None, key
        resolved_ids.update(definition.technique_ids)

    assert resolved_ids == EXPECTED_TECHNIQUE_IDS
    for technique_id in sorted(resolved_ids):
        technique = registry.get(technique_id)
        # dirección de autoridad: si el operador existe y se declara en el
        # dispatch, el canon DEBE haberlo promocionado por su cadena propia
        # (§79); si no, el dispatch estaría ejecutando sin autoridad.
        assert technique.status == "IMPLEMENTED", (
            f"{technique_id}: operador con módulo real sin promoción canónica"
        )
        assert technique.implementation
        assert technique.input_contracts
        assert technique.output_contracts
        assert technique.tests
    # dirección inversa: ninguna técnica IMPLEMENTED de invención carece de
    # operador dispatchable (falsa capacidad declarada).
    invention_implemented = {
        t.id for t in registry.all()
        if t.status.startswith("IMPLEMENTED")
        and t.implementation and "invention" in t.implementation
    }
    assert invention_implemented <= resolved_ids, (
        "IMPLEMENTED sin operador dispatch: " + str(invention_implemented - resolved_ids)
    )
