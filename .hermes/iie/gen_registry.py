"""P01-T05: build data/intelligence/technique_registry.yaml from reg_parts/*.txt.

Pipe-separated rows: id|name|owner_code|module|phases|pipelines|model|cost|net
"""
from __future__ import annotations

import os
from collections import OrderedDict

BASE = os.path.dirname(os.path.abspath(__file__))
OWNER = {"IIE": "CRIBA_IIE", "CR": "CRIBA", "CSI": "CRIBA_PLUS_IIE", "SUPRA": "SUPRA_ORCHESTRATION"}
FAMILY = {  # by id range, addendum sections 87-94
    (1, 9): "PATENT_INTELLIGENCE", (10, 30): "EXTERNAL_SOURCES",
    (31, 45): "RETRIEVAL_GRAPH", (46, 52): "TOPIC_DYNAMICS",
    (53, 79): "INVENTION", (80, 95): "NOVELTY_KNOWLEDGE_GRAPH",
    (96, 115): "SIGNALS_EVIDENCE_OPPORTUNITY", (116, 130): "ADVERSARIAL_FUTURES",
}
SUBS = {
    "T126": ["unmet needs", "review mining", "workaround mining", "workflow friction"],
    "T127": ["human bottleneck", "API unlock", "hardware unlock", "dataset unlock", "model unlock", "open-source unlock"],
    "T128": ["patent expiration", "abandoned IP", "dormant papers", "sleeping beauties"],
    "T129": ["second-order effects", "N-th-order effects", "counterfactual", "future-back", "bottleneck mapping"],
    "T130": ["S-curve detection", "substitution curves", "innovation genealogy"],
}

# Phase-owned capability metadata.  This generator is the single writable
# source for technique_registry.yaml; techniques absent here remain PLANNED.
# Historial: cbac469 elimino invention/* con el registro aun marcando 11
# IMPLEMENTED (corregido en canon 2026-09-07.2, 0 IMPLEMENTED). Los modulos
# y tests fueron RESTAURADOS desde cbac469~1 el 2026-09-08 (commit de
# restauracion); toda IMPLEMENTED se verifica contra codigo y tests reales
# en tests/intelligence/test_technique_runtime_traceability.py.
IMPLEMENTATION_OVERRIDES = {
    "T053": {
        "implementation": "criba.intelligence.invention.rare_combinations.detect_rare_combinations",
        "input_contracts": ["Sequence[EvidenceDocument] with metadata.concepts"],
        "output_contracts": ["list[InventionCandidate]"],
        "tests": ["test_rare_combinations_are_deterministic_and_explicitly_corpus_local"],
    },
    "T055": {
        "implementation": "criba.intelligence.invention.cross_domain.detect_cross_domain_analogies",
        "input_contracts": ["Sequence[EvidenceDocument] with metadata.domain and metadata.concepts"],
        "output_contracts": ["list[InventionCandidate]"],
        "tests": ["test_cross_domain_analogies_require_explicit_shared_concepts_and_domains"],
    },
    "T057": {
        "implementation": "criba.intelligence.invention.triz.list_principles/get_principle",
        "input_contracts": ["principle number: int (1..40)"],
        "output_contracts": ["tuple[TrizPrinciple, ...]"],
        "tests": [
            "test_registry_contains_exactly_40_principles",
            "test_numbers_unique_and_cover_1_to_40",
            "test_order_is_stable_across_calls",
            "test_lookup_valid_returns_matching_principle",
            "test_lookup_invalid_raises_key_error",
        ],
    },
    "T059": {
        "implementation": "criba.intelligence.invention.morphology.generate_morphological_hypotheses",
        "input_contracts": ["problem: str", "dimensions: Mapping[str, Sequence[str]]"],
        "output_contracts": ["list[InventionCandidate]"],
        "tests": ["test_t059_morphological_analysis_generates_deterministic_hypotheses"],
    },
    "T060": {
        "implementation": "criba.intelligence.invention.scamper.generate_scamper_hypotheses",
        "input_contracts": ["problem: str", "components: Sequence[str]"],
        "output_contracts": ["list[InventionCandidate]"],
        "tests": ["test_scamper_generates_all_seven_question_types_without_claiming_solution"],
    },
    "T062": {
        "implementation": "criba.intelligence.invention.functions.decompose_functional_hypotheses",
        "input_contracts": ["problem: str", "component_functions: Mapping[str, Sequence[str]]"],
        "output_contracts": ["list[InventionCandidate]"],
        "tests": ["test_t062_functional_decomposition_is_explicit_and_deterministic"],
    },
    "T063": {
        "implementation": "criba.intelligence.invention.functions.search_function_to_mechanism_hypotheses",
        "input_contracts": ["problem: str", "functions: Sequence[str]", "retrieved EvidenceDocument metadata.function_mechanisms"],
        "output_contracts": ["list[InventionCandidate] with source doc_id in description"],
        "tests": ["test_t063_function_to_mechanism_search_requires_explicit_source_metadata"],
    },
    "T064": {
        "implementation": "criba.intelligence.invention.first_principles.decompose_first_principles_hypotheses",
        "input_contracts": ["problem: str", "premise_implications: Mapping[str, Sequence[str]]"],
        "output_contracts": ["list[InventionCandidate]"],
        "tests": ["test_t064_first_principles_decomposition_keeps_premises_explicit"],
    },
    "T065": {
        "implementation": "criba.intelligence.invention.inversion.generate_constraint_inversion_hypotheses",
        "input_contracts": ["problem: str", "constraint_inversions: Mapping[str, Sequence[str]]"],
        "output_contracts": ["list[InventionCandidate]"],
        "tests": ["test_t065_constraint_inversion_never_claims_constraint_is_removed"],
    },
    "T116": {
        "implementation": "criba.intelligence.invention.adjacent_possible.generate_adjacent_possible_hypotheses",
        "input_contracts": ["problem: str", "capabilities: Sequence[str]", "known_combinations: Sequence[Sequence[str]]"],
        "output_contracts": ["list[InventionCandidate]"],
        "tests": ["test_t116_adjacent_possible_excludes_explicit_known_combinations"],
    },
    "T019": {
        "implementation": "criba.intelligence.signals.dynamics.TopicDynamics.acceleration",
        "input_contracts": ["observations: Sequence[TopicObservation]", "topic: str"],
        "output_contracts": ["list[float] period-aligned"],
        "tests": ["test_topic_dynamics_aligns_velocity_and_acceleration_to_periods"],
    },
    "T048": {
        "implementation": "criba.intelligence.signals.dynamics.TopicDynamics.velocity",
        "input_contracts": ["observations: Sequence[TopicObservation]", "topic: str"],
        "output_contracts": ["list[float] period-aligned"],
        "tests": ["test_topic_dynamics_aligns_velocity_and_acceleration_to_periods"],
    },
    "T049": {
        "implementation": "criba.intelligence.signals.dynamics.TopicDynamics.acceleration",
        "input_contracts": ["observations: Sequence[TopicObservation]", "topic: str"],
        "output_contracts": ["list[float] period-aligned"],
        "tests": ["test_topic_dynamics_aligns_velocity_and_acceleration_to_periods"],
    },
    "T067": {
        "implementation": "criba.intelligence.gaps.contradictions.analyze_contradictions",
        "input_contracts": ["claims from documents via claims.extract_claims_from_fragments"],
        "output_contracts": ["list[Contradiction]"],
        "tests": ["test_detects_opposing_claims_and_unites_document_provenance",
                  "test_is_deterministic_and_ignores_unparseable_or_same_polarity_claims"],
    },
    "T068": {
        "implementation": "criba.intelligence.gaps.research.extract_research_gaps",
        "input_contracts": ["documents: Sequence[EvidenceDocument]", "topic: str = ''"],
        "output_contracts": ["list[Gap]"],
        "tests": ["test_extracts_only_cued_sentences_with_provenance",
                  "test_extraction_is_deterministic_and_deduplicates_same_document"],
    },
    "T069": {
        "implementation": "criba.intelligence.gaps.limitations.extract_limitations",
        "input_contracts": ["documents: Sequence[EvidenceDocument]", "scope: str = ''"],
        "output_contracts": ["list[Limitation]"],
        "tests": ["test_extracts_limitations_with_stable_provenance_and_scope",
                  "test_resolved_limitation_language_is_not_promoted"],
    },
    "T070": {
        "implementation": "criba.intelligence.gaps.failures.extract_failures",
        "input_contracts": ["documents: Sequence[EvidenceDocument]", "topic: str = ''"],
        "output_contracts": ["list[FailureCase]"],
        "tests": ["test_mines_failure_cases_with_mode_and_provenance",
                  "test_resolved_failure_language_is_not_promoted"],
    },
    "T071": {
        "implementation": "criba.intelligence.gaps.resurrection.extract_resurrection_candidates",
        "input_contracts": ["documents: Sequence[EvidenceDocument]", "topic: str = ''"],
        "output_contracts": ["list[ResurrectionCandidate]"],
        "tests": ["test_extracts_structured_resurrection_with_provenance",
                  "test_text_extraction_requires_current_evidence_of_constraint_change"],
    },
    "T086": {
        "implementation": "criba.intelligence.gaps.white_space.analyze_white_spaces",
        "input_contracts": ["documents: Sequence[EvidenceDocument]", "space_type: str = ''", "topic: str = ''"],
        "output_contracts": ["list[WhiteSpaceCandidate]"],
        "tests": ["test_analyzes_white_spaces_with_type_and_provenance",
                  "test_analysis_is_deterministic_deduplicated_and_topic_filtered"],
    },
    "T096": {
        "implementation": "criba.intelligence.signals.bursts.BurstDetector.detect",
        "input_contracts": ["observations: Sequence[TopicObservation]", "topic: str | None = None"],
        "output_contracts": ["list[BurstEvent]"],
        "tests": ["test_burst_detector_returns_velocity_spikes_with_period_and_strength"],
    },
    "T097": {
        "implementation": "criba.intelligence.signals.changepoints.ChangePointDetector.detect",
        "input_contracts": ["observations: Sequence[TopicObservation]", "topic: str | None = None"],
        "output_contracts": ["list[ChangePointEvent]"],
        "tests": ["test_change_point_detector_reports_level_shift_at_candidate_period"],
    },
    "T098": {
        "implementation": "criba.intelligence.signals.anomaly.AnomalyDetector.detect",
        "input_contracts": ["observations: Sequence[TopicObservation]", "topic: str | None = None"],
        "output_contracts": ["list[AnomalyEvent]"],
        "tests": ["test_anomaly_detector_reports_robust_frequency_outlier"],
    },
    "T099": {
        "implementation": "criba.intelligence.signals.weak_signals.WeakSignalAggregator.aggregate",
        "input_contracts": ["signals: Sequence[WeakSignal]"],
        "output_contracts": ["list[WeakSignal] merged"],
        "tests": ["test_weak_signal_aggregator_merges_support_without_double_counting_ids"],
    },
    "T101": {
        "implementation": "criba.intelligence.signals.lead_lag.LeadLagAnalyzer.analyze",
        "input_contracts": ["observations: Sequence[TopicObservation]", "leader_topic: str", "follower_topic: str"],
        "output_contracts": ["LeadLagResult | None"],
        "tests": ["test_lead_lag_analyzer_identifies_delayed_follower"],
    },
    "T128": {
        "implementation": "criba.intelligence.gaps.{patent_expiration,dormant,sleeping_beauty,resurrection}",
        "input_contracts": ["documents: Sequence[EvidenceDocument] con metadata/fragments de expiración, sueño o abandono"],
        "output_contracts": ["list[PatentExpirationOpportunity|DormantPaperCandidate|SleepingBeautyCandidate|ResurrectionCandidate]"],
        "tests": ["test_analyzes_structured_opportunity_without_declaring_freedom_to_operate",
                  "test_detects_old_paper_with_explicit_low_attention_evidence",
                  "test_detects_delayed_attention_from_citation_series"],
    },
    "T129": {
        "implementation": "criba.intelligence.invention.{counterfactual,future_back,bottlenecks,nth_order}",
        "input_contracts": ["problem: str", "caller-supplied temporal/counterfactual mappings"],
        "output_contracts": ["list[InventionCandidate]"],
        "tests": [
            "test_t129_counterfactual_keeps_alternate_outcomes_as_hypotheses",
            "test_t129_future_back_never_claims_the_future_state_will_be_reached",
            "test_t129_bottleneck_mapping_never_claims_the_bottleneck_is_causal",
            "test_t129_nth_order_effects_never_claim_the_effect_chain_will_occur",
        ],
    },
}

def family_of(tid: str) -> str:
    n = int(tid[1:])
    for (a, b), fam in FAMILY.items():
        if a <= n <= b:
            return fam
    raise ValueError(tid)

def slug(name: str) -> str:
    keep = "abcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(c if c in keep else "_" for c in name.lower()).strip("_")[:48]

def yq(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

rows = OrderedDict()
for part in ("p1", "p2", "p3", "p4"):
    with open(os.path.join(BASE, "reg_parts", f"{part}.txt"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            fields = line.split("|")
            assert len(fields) == 9, f"{part}: {len(fields)} fields in {fields[0]}"
            rows[fields[0]] = fields

ids = list(rows)
expected = [f"T{i:03d}" for i in range(1, 131)]
missing = [t for t in expected if t not in rows]
extra = [t for t in ids if t not in expected]
if missing or extra:
    raise SystemExit(f"MISSING={missing} EXTRA={extra}")

CANON_VERSION = "2026-09-08.2"  # bump when reg_parts/*.txt or overrides change

out = [
    "# CRIBA IIE technique registry - T001-T130 (GENERATED by gen_registry.py; do not edit by hand)",
    "",
    "schema_version: 2",
    f"canon_version: {yq(CANON_VERSION)}",
    "provenance:",
    "  source: \"ADDENDUM 'INTEGRACION EXHAUSTIVA DE LAS 130 TECNICAS' secciones 87-94\"",
    "  generator: .hermes/iie/gen_registry.py",
    "  parts:",
] + [f"    - .hermes/iie/reg_parts/{part}.txt" for part in ("p1", "p2", "p3", "p4")]
out += ["techniques:", ""]
for tid, f in rows.items():
    rid, name, oc, module, phases, pipelines, model, cost, net = f
    override = IMPLEMENTATION_OVERRIDES.get(tid, {})
    status = "IMPLEMENTED" if override else "PLANNED"
    implementation = override.get("implementation")
    input_contracts = override.get("input_contracts", [])
    output_contracts = override.get("output_contracts", [])
    tests = override.get("tests", [f"test_{rid.lower()}_{slug(name)}"])
    out += [
        f"- id: {rid}",
        f"  name: {yq(name)}",
        f"  family: {family_of(tid)}",
        f"  owner: {OWNER[oc]}",
        "  module:",
    ]
    out += [f"    - criba.intelligence.{m}" for m in module.replace(" ", "").split("+")]
    out += ["  phase:"] + [f"    - {p}" for p in phases.split("+")]
    out += ["  pipelines:"] + [f"    - {p}" for p in pipelines.replace(" ", "").split("+")]
    out += [
        "  model:",
        "    default: GLM-5.3",
        f"    reasoning: {model.replace('lowhigh', 'low|high')}",
        f"  cost_class: {cost}",
        f"  requires_network: {'true' if net == '1' else 'false'}",
        "  requires_credentials: false",
        f"  status: {status}",
        f"  implementation: {yq(implementation) if implementation else 'null'}",
    ]
    for field, values, quote_values in (
        ("input_contracts", input_contracts, True),
        ("output_contracts", output_contracts, True),
        ("tests", tests, False),
    ):
        if not values:
            out.append(f"  {field}: []")
            continue
        out.append(f"  {field}:")
        out += [f"    - {yq(value) if quote_values else value}" for value in values]
    if tid in SUBS:
        out.append("  subtechniques:")
        out += [f"    - {yq(s)}" for s in SUBS[tid]]
    out.append("")

# Derive the destination from BASE (repo checkout or portable bundle): this
# script reads reg_parts/ relative to itself, so it must also write relative
# to itself instead of a hardcoded absolute path (qa P2-3).
dest = os.path.normpath(os.path.join(
    BASE, "..", "..", "data", "intelligence", "technique_registry.yaml"))
os.makedirs(os.path.dirname(dest), exist_ok=True)
with open(dest, "w", encoding="utf-8") as fh:
    fh.write("\n".join(out) + "\n")
print(f"OK: {len(rows)} techniques -> {dest}")
