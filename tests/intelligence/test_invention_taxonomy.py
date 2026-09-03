"""Contract tests for the frozen P09 invention operator taxonomy."""
from __future__ import annotations

import pytest

from criba.intelligence.contracts import InventionCandidate
from criba.intelligence.contracts import EvidenceDocument
from criba.intelligence.invention import (
    OPERATORS_BY_KEY,
    OperatorContext,
    OperatorRegistry,
    get_operator,
    operator_definitions,
    detect_rare_combinations,
    detect_cross_domain_analogies,
    generate_scamper_hypotheses,
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
