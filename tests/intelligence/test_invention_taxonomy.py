"""Contract tests for the frozen P09 invention operator taxonomy."""
from __future__ import annotations

import pytest

from criba.intelligence.contracts import EvidenceDocument, InventionCandidate
from criba.intelligence.invention import (
    OPERATORS_BY_KEY,
    OperatorContext,
    OperatorRegistry,
    decompose_first_principles_hypotheses,
    decompose_functional_hypotheses,
    detect_cross_domain_analogies,
    detect_rare_combinations,
    generate_adjacent_possible_hypotheses,
    generate_bottleneck_mapping_hypotheses,
    generate_constraint_inversion_hypotheses,
    generate_counterfactual_hypotheses,
    generate_future_back_hypotheses,
    generate_morphological_hypotheses,
    generate_nth_order_effect_hypotheses,
    generate_scamper_hypotheses,
    get_operator,
    operator_definitions,
    search_function_to_mechanism_hypotheses,
)


def test_taxonomy_is_complete_for_blueprint_invention_techniques():
    technique_ids = {technique for operator in operator_definitions() for technique in operator.technique_ids}
    assert {f"T{number:03d}" for number in range(53, 68)} <= technique_ids
    assert "T129" in technique_ids
    assert len(OPERATORS_BY_KEY) == len(operator_definitions())


def test_taxonomy_lookup_is_stable_and_does_not_make_up_unknown_operators():
    operator = get_operator("function_to_mechanism")
    assert operator is not None
    assert operator.technique_ids == ("T063",)
    assert get_operator("unsupported_magic_operator") is None


def test_taxonomy_mapping_cannot_be_mutated_by_consumers():
    with pytest.raises(TypeError):
        OPERATORS_BY_KEY["invented"] = get_operator("triz")


def test_registry_executes_only_declared_and_traceable_operators():
    registry = OperatorRegistry()
    context = OperatorContext(problem="reduce heat")
    with pytest.raises(LookupError, match="no registered"):
        registry.execute("triz", context)
    with pytest.raises(KeyError, match="unknown"):
        registry.register("invented", lambda _: [])

    registry.register(
        "triz",
        lambda _: [InventionCandidate(title="Heat transfer alternative", operators=("T057",))],
    )
    assert registry.registered_keys() == ("triz",)
    assert registry.execute("triz", context)[0].operators == ("T057",)


def test_registry_rejects_duplicate_registration_and_untraceable_output():
    registry = OperatorRegistry()
    registry.register("triz", lambda _: [InventionCandidate(title="Missing trace")])
    with pytest.raises(ValueError, match="already registered"):
        registry.register("triz", lambda _: [])
    with pytest.raises(ValueError, match="traceability"):
        registry.execute("triz", OperatorContext(problem="reduce heat"))


def test_rare_combinations_are_deterministic_and_explicitly_corpus_local():
    documents = [
        EvidenceDocument(doc_id="d2", metadata={"concepts": ["optics", "cooling"]}),
        EvidenceDocument(doc_id="d1", metadata={"concepts": ["optics", "cooling"]}),
        EvidenceDocument(doc_id="d3", metadata={"concepts": ["cooling", "biology"]}),
    ]
    candidates = detect_rare_combinations(documents)
    assert [candidate.title for candidate in candidates] == ["Explore biology + cooling"]
    assert candidates[0].operators == ("T053",)
    assert "not a global novelty" in candidates[0].description


def test_rare_combinations_validate_limits_and_ignore_unsupported_metadata():
    doc = EvidenceDocument(doc_id="d1", metadata={"concepts": "not a sequence"})
    assert detect_rare_combinations([doc]) == []
    with pytest.raises(ValueError, match="frequency"):
        detect_rare_combinations([], max_frequency=0)
    with pytest.raises(ValueError, match="limit"):
        detect_rare_combinations([], limit=-1)


def test_cross_domain_analogies_require_explicit_shared_concepts_and_domains():
    documents = [
        EvidenceDocument(doc_id="heat", metadata={"domain": "thermal", "concepts": ["phase change"]}),
        EvidenceDocument(doc_id="storage", metadata={"domain": "battery", "concepts": ["phase change"]}),
        EvidenceDocument(doc_id="ignored", metadata={"concepts": ["phase change"]}),
    ]
    candidates = detect_cross_domain_analogies(documents)
    assert [candidate.title for candidate in candidates] == ["Transfer phase change: battery → thermal"]
    assert candidates[0].operators == ("T055",)
    assert "not evidence" in candidates[0].description


def test_cross_domain_analogies_validate_limit():
    with pytest.raises(ValueError, match="limit"):
        detect_cross_domain_analogies([], limit=-1)


def test_t059_morphological_analysis_generates_deterministic_hypotheses():
    candidates = generate_morphological_hypotheses(
        "reduce heat",
        {"material": ["graphite", "copper"], "geometry": ["plate", "fin"]},
        limit=3,
    )

    assert [candidate.title for candidate in candidates] == [
        "Morphology: geometry=fin; material=copper",
        "Morphology: geometry=fin; material=graphite",
        "Morphology: geometry=plate; material=copper",
    ]
    assert all(candidate.operators == ("T059",) for candidate in candidates)
    assert all("not evidence" in candidate.description for candidate in candidates)
    assert all(candidate.epistemic_state.value == "HYPOTHESIS" for candidate in candidates)


def test_t062_functional_decomposition_is_explicit_and_deterministic():
    candidates = decompose_functional_hypotheses(
        "reduce battery heat",
        {
            "thermal system": ["route coolant", "reject heat"],
            "control": ["measure temperature"],
        },
    )

    assert [candidate.title for candidate in candidates] == [
        "Function: control → measure temperature",
        "Function: thermal system → reject heat",
        "Function: thermal system → route coolant",
    ]
    assert all(candidate.operators == ("T062",) for candidate in candidates)
    assert all("not evidence" in candidate.description for candidate in candidates)
    assert all(candidate.mechanism == "" for candidate in candidates)


def test_t063_function_to_mechanism_search_requires_explicit_source_metadata():
    documents = [
        EvidenceDocument(
            doc_id="d2",
            metadata={"function_mechanisms": {"reject heat": ["phase change"]}},
        ),
        EvidenceDocument(
            doc_id="d1",
            metadata={"function_mechanisms": {"reject heat": ["microchannel"]}},
        ),
        EvidenceDocument(doc_id="ignored", metadata={"mechanisms": ["fan"]}),
    ]

    candidates = search_function_to_mechanism_hypotheses(
        "reduce battery heat",
        ["reject heat"],
        documents,
    )

    assert [candidate.title for candidate in candidates] == [
        "Mechanism: reject heat → microchannel",
        "Mechanism: reject heat → phase change",
    ]
    assert [candidate.mechanism for candidate in candidates] == ["microchannel", "phase change"]
    assert all(candidate.operators == ("T063",) for candidate in candidates)
    assert "d1" in candidates[0].description
    assert all("not evidence" in candidate.description for candidate in candidates)


def test_t064_first_principles_decomposition_keeps_premises_explicit():
    candidates = decompose_first_principles_hypotheses(
        "reduce battery heat",
        {
            "heat flows down a temperature gradient": ["lower thermal resistance"],
            "energy is conserved": ["measure where losses become heat"],
        },
    )

    assert [candidate.title for candidate in candidates] == [
        "First principle: energy is conserved → measure where losses become heat",
        "First principle: heat flows down a temperature gradient → lower thermal resistance",
    ]
    assert all(candidate.operators == ("T064",) for candidate in candidates)
    assert all("not evidence" in candidate.description for candidate in candidates)
    assert all(candidate.mechanism == "" for candidate in candidates)


def test_t065_constraint_inversion_never_claims_constraint_is_removed():
    candidates = generate_constraint_inversion_hypotheses(
        "reduce battery heat",
        {
            "only CPU is available": ["dedicated GPU is available"],
            "must operate offline": ["continuous network access is available"],
        },
    )

    assert [candidate.title for candidate in candidates] == [
        "Constraint inversion: must operate offline → continuous network access is available",
        "Constraint inversion: only CPU is available → dedicated GPU is available",
    ]
    assert all(candidate.operators == ("T065",) for candidate in candidates)
    assert all("not evidence" in candidate.description for candidate in candidates)
    assert all("does not establish that the constraint is removed" in candidate.description for candidate in candidates)


def test_t116_adjacent_possible_excludes_explicit_known_combinations():
    candidates = generate_adjacent_possible_hypotheses(
        "reduce battery heat",
        ["battery cycling", "thermal sensing", "phase change"],
        known_combinations=[("battery cycling", "phase change")],
    )

    assert [candidate.title for candidate in candidates] == [
        "Adjacent possible: battery cycling + thermal sensing",
        "Adjacent possible: phase change + thermal sensing",
    ]
    assert all(candidate.operators == ("T116",) for candidate in candidates)
    assert get_operator("adjacent_possible").technique_ids == ("T116",)
    assert all("not evidence" in candidate.description for candidate in candidates)


def test_t129_counterfactual_keeps_alternate_outcomes_as_hypotheses():
    candidates = generate_counterfactual_hypotheses(
        "reduce battery heat",
        {"no thermal sensor": ["temperature drift is unobserved"]},
    )

    assert [candidate.title for candidate in candidates] == [
        "Counterfactual: no thermal sensor → temperature drift is unobserved",
    ]
    assert candidates[0].operators == ("T129",)
    assert "not evidence" in candidates[0].description
    assert "does not predict the outcome" in candidates[0].description


def test_t129_future_back_never_claims_the_future_state_will_be_reached():
    candidates = generate_future_back_hypotheses(
        "reduce battery heat",
        {"thermal control is deployed": ["validate sensor calibration"]},
    )

    assert [candidate.title for candidate in candidates] == [
        "Future-back: thermal control is deployed ← validate sensor calibration",
    ]
    assert candidates[0].operators == ("T129",)
    assert "not evidence" in candidates[0].description
    assert "does not establish that the future state will be reached" in candidates[0].description


def test_t129_bottleneck_mapping_never_claims_the_bottleneck_is_causal():
    candidates = generate_bottleneck_mapping_hypotheses(
        "reduce battery heat",
        {"thermal interface resistance": ["measure junction-to-case gradient"]},
    )

    assert [candidate.title for candidate in candidates] == [
        "Bottleneck map: thermal interface resistance → measure junction-to-case gradient",
    ]
    assert candidates[0].operators == ("T129",)
    assert "not evidence" in candidates[0].description
    assert "does not establish causality" in candidates[0].description


def test_t129_nth_order_effects_never_claim_the_effect_chain_will_occur():
    candidates = generate_nth_order_effect_hypotheses(
        "reduce battery heat",
        {
            "add thermal sensor": [
                ("measure temperature", "adjust cooling", "increase cycling wear"),
            ],
        },
    )

    assert [candidate.title for candidate in candidates] == [
        "Nth-order: add thermal sensor → measure temperature → adjust cooling → increase cycling wear",
    ]
    assert candidates[0].operators == ("T129",)
    assert "not evidence" in candidates[0].description
    assert "does not establish that the effect chain will occur" in candidates[0].description


def test_scamper_generates_all_seven_question_types_without_claiming_solution():
    candidates = generate_scamper_hypotheses("reduce heat", ["heat sink"])
    assert len(candidates) == 7
    assert [candidate.title.split(":")[0] for candidate in candidates] == [
        "Substitute", "Combine", "Adapt", "Modify", "Put to another use", "Eliminate", "Reverse",
    ]
    assert all(candidate.operators == ("T060",) for candidate in candidates)
    assert all("not evidence" in candidate.description for candidate in candidates)


def test_scamper_validates_problem_limit_and_deduplicates_components():
    with pytest.raises(ValueError, match="problem"):
        generate_scamper_hypotheses(" ", ["heat sink"])
    with pytest.raises(ValueError, match="limit"):
        generate_scamper_hypotheses("reduce heat", ["heat sink"], limit=-1)
    assert len(generate_scamper_hypotheses("reduce heat", ["heat sink", " heat sink "])) == 7
