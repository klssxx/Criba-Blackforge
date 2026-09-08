"""P001–P130 fichas: data/intelligence/technique_fichas.yaml (GENERATED).

Consolida por técnica, sin inventar nada:
- requisito canónico (reg_parts → gen_registry canon);
- estado REAL materializado (IMPLEMENTED/PLANNED + GAP documentado);
- operador runtime y ruta de integración cuando existen;
- tests positivos/negativos declarados;
- divergencia de nombre blueprint §72 vs reg_parts (reg_parts es canon);
- falsifier y remaining_gap de docs/recovery/CBAC469_AUDIT.md (curados).

Fuente de verdad: technique_registry.yaml (generado). Este archivo NUNCA
redefine status; solo documenta y referencia. Editar vía gen_fichas.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import yaml  # noqa: E402

from criba.intelligence.registry import TechniqueRegistry  # noqa: E402

REGISTRY_PATH = ROOT / "data" / "intelligence" / "technique_registry.yaml"
BLUEPRINT = ROOT.parent.parent / "ARCHIVE" / "master-pack-v2.1" / "CRIBA_BLUEPRINT_ULTIMATE.txt"
DEST = ROOT / "data" / "intelligence" / "technique_fichas.yaml"

# Checkpoints curados por técnica (de la auditoría slices 1-3). Todo lo no
# listado queda MAPPED_ONLY/PLANNED con remaining_gap honesto.
CHECKPOINTS: dict[str, dict] = {
    # -- slice 1: invention/ -------------------------------------------------
    "T053": {"operator": "rare_combinations.detect_rare_combinations", "falsifier": "afirmar novedad global o no determinismo con mismo corpus", "remaining_gap": "consumidor en loop invent (decisión de arquitectura vigente)"},
    "T055": {"operator": "cross_domain.detect_cross_domain_analogies", "falsifier": "analogía sin conceptos compartidos explícitos", "remaining_gap": "ídem"},
    "T057": {"operator": "triz.list_principles/get_principle", "falsifier": "catálogo mutable o fuera de 1..40", "remaining_gap": "aplicación a contradicciones es T058 (PLANNED)"},
    "T059": {"operator": "morphology.generate_morphological_hypotheses", "falsifier": "hipótesis fuera del producto cartesiano declarado", "remaining_gap": "ídem T053"},
    "T060": {"operator": "scamper.generate_scamper_hypotheses", "falsifier": "menos de 7 tipos o afirmar resolver", "remaining_gap": "ídem"},
    "T062": {"operator": "functions.decompose_functional_hypotheses", "falsifier": "inventar funciones no declaradas", "remaining_gap": "ídem"},
    "T063": {"operator": "functions.search_function_to_mechanism_hypotheses", "falsifier": "mecanismo sin doc_id fuente", "remaining_gap": "requiere evidencia recuperada (fuentes en REFRESH)"},
    "T064": {"operator": "first_principles.decompose_first_principles_hypotheses", "falsifier": "ocultar la premisa de la que deriva", "remaining_gap": "ídem"},
    "T065": {"operator": "inversion.generate_constraint_inversion_hypotheses", "falsifier": "afirmar que la restricción desaparece", "remaining_gap": "ídem"},
    "T116": {"operator": "adjacent_possible.generate_adjacent_possible_hypotheses", "falsifier": "proponer par presente en known_combinations", "remaining_gap": "ídem"},
    "T129": {"operator": "counterfactual/future_back/bottlenecks/nth_order (4 generadores)", "falsifier": "efecto futuro afirmado como ocurrirá; cuello como causal", "remaining_gap": "ídem"},
    # -- slice 2: gaps/signals ------------------------------------------------
    "T019": {"operator": "signals.dynamics.TopicDynamics.acceleration", "falsifier": "aceleración desalineada a periodos", "remaining_gap": "integración en loop RADAR (no existe aún)"},
    "T048": {"operator": "signals.dynamics.TopicDynamics.velocity", "falsifier": "deltas no alineadas", "remaining_gap": "ídem"},
    "T049": {"operator": "signals.dynamics.TopicDynamics.acceleration", "falsifier": "ídem T019", "remaining_gap": "ídem"},
    "T067": {"operator": "gaps.contradictions.analyze_contradictions", "falsifier": "contradicción sin ambas procedencias o misma polaridad", "remaining_gap": "claims desde fuentes en vivo (REFRESH)"},
    "T068": {"operator": "gaps.research.extract_research_gaps", "falsifier": "gap sin cue léxica", "remaining_gap": "ídem"},
    "T069": {"operator": "gaps.limitations.extract_limitations", "falsifier": "limitación resuelta promocionada", "remaining_gap": "ídem"},
    "T070": {"operator": "gaps.failures.extract_failures", "falsifier": "modo inventado para fallo no estructurado", "remaining_gap": "ídem"},
    "T071": {"operator": "gaps.resurrection.extract_resurrection_candidates", "falsifier": "resurrección sin evidencia del cambio de restricción", "remaining_gap": "ídem"},
    "T086": {"operator": "gaps.white_space.analyze_white_spaces", "falsifier": "white-space sin procedencia", "remaining_gap": "T087-89 por tipo: detector genérico (gap)"},
    "T096": {"operator": "signals.bursts.BurstDetector.detect", "falsifier": "burst sin periodo/fuerza", "remaining_gap": "integración RADAR"},
    "T097": {"operator": "signals.changepoints.ChangePointDetector.detect", "falsifier": "cambio en serie plana", "remaining_gap": "ídem"},
    "T098": {"operator": "signals.anomaly.AnomalyDetector.detect", "falsifier": "outlier por media no robusta", "remaining_gap": "ídem"},
    "T099": {"operator": "signals.weak_signals.WeakSignalAggregator.aggregate", "falsifier": "doble conteo de soporte", "remaining_gap": "ídem"},
    "T101": {"operator": "signals.lead_lag.LeadLagAnalyzer.analyze", "falsifier": "lag positivo para el líder", "remaining_gap": "ídem"},
    "T128": {"operator": "patent_expiration+dormant+sleeping_beauty+resurrection", "falsifier": "expiración sin fecha o FTO afirmado", "remaining_gap": "ídem"},
    # -- slice 3: graph -------------------------------------------------------
    "T091": {"operator": "graph.link_prediction.LinkPredictionInterface.predict", "falsifier": "predicción sin vecinos comunes o con enlaces existentes", "remaining_gap": "grafo alimentado desde extracción de entidades en vivo"},
    "T094": {"operator": "graph.communities.CommunityDetector.detect", "falsifier": "comunidad no ordenada o fuera de subset", "remaining_gap": "ídem"},
    "T095": {"operator": "graph.bridges.BridgeNodeAnalyzer.articulation_points", "falsifier": "articulación en un ciclo", "remaining_gap": "ídem"},
}

# GAPs canónicos documentados (canon referencia módulo/capacidad inexistente).
GAPS: dict[str, str] = {
    "T093": "graph.embeddings nunca existió (no está en el diff de cbac469): GAP canónico",
    "T003": "entities.ontology referenciado por el canon y jamás implementado",
    "T034": "ídem entities.ontology",
}


def blueprint_names() -> dict[str, str]:
    """Nombres del blueprint §72 (evidencia histórica, reg_parts es canon)."""
    try:
        lines = BLUEPRINT.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    import re

    out = {}
    for line in lines:
        m = re.match(r"^(T\d{3}) (.+)$", line.strip())
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def main() -> None:
    registry = TechniqueRegistry(REGISTRY_PATH)
    bp = blueprint_names()
    fichas: list[dict] = []
    for t in registry.all():
        cp = CHECKPOINTS.get(t.id, {})
        status = t.status
        if t.status == "PLANNED" and t.id in GAPS:
            # canon referencia un módulo/capacidad que jamás se materializó
            status = "MAPPED_ONLY_PLANNED"
        ficha = {
            "id": t.id,
            "canonical_requirement": t.name,
            "blueprint_72_name": bp.get(t.id, "UNKNOWN"),
            "name_divergence": bool(bp.get(t.id) and bp[t.id] != t.name),
            "family": t.family,
            "owner": t.owner,
            "phase": list(t.phase),
            "pipelines": list(t.pipelines),
            "status": status,
            "implementation": t.implementation,
            "runtime_operator": cp.get("operator"),
            "integration_path": "criba tecnicas --ejecutar (execution.py)" if cp.get("operator") else None,
            "input_contracts": list(t.input_contracts),
            "output_contracts": list(t.output_contracts),
            "tests": list(t.tests),
            "provenance": "reg_parts → gen_registry.py (canon) + CBAC469 slices 1-3" if cp else "reg_parts → gen_registry.py (canon)",
            "gap": GAPS.get(t.id),
            "remaining_gap": cp.get("remaining_gap", "implementación no materializada — construcción nueva requerida (dimensionar por EV)" if t.status == "PLANNED" else None),
            "falsifier": cp.get("falsifier"),
        }
        fichas.append(ficha)

    implemented = sum(1 for f in fichas if f["status"].startswith("IMPLEMENTED"))
    doc = {
        "schema_version": 1,
        "generated_by": ".hermes/iie/gen_fichas.py",
        "canon_version": registry.canon_version,
        "provenance_note": "reg_parts es canon; blueprint §72 es evidencia histórica (17 divergencias documentadas por técnica). Nada de este archivo redefine status del canon.",
        "summary": {
            "total": len(fichas),
            "implemented": implemented,
            "planned": sum(1 for f in fichas if f["status"] == "PLANNED"),
            "mapped_only_planned": sum(1 for f in fichas if f["status"] == "MAPPED_ONLY_PLANNED"),
            "canonical_gaps": len(GAPS),
        },
        "fichas": fichas,
    }
    DEST.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"OK: {len(fichas)} fichas -> {DEST} (implemented={implemented})")


if __name__ == "__main__":
    main()
