"""P10-T01: adversarial prior-art protocol contract."""
from __future__ import annotations

import pytest

from criba.intelligence.prior_art import (
    AdversarialSearchProtocol,
    PriorArtStage,
    build_query_lattice,
)


def test_adversarial_protocol_is_ordered_bounded_and_forbids_proven_new():
    protocol = AdversarialSearchProtocol(
        candidate_id="cand_001",
        max_prior_art_rounds=2,
        max_mutations_per_candidate=2,
    )

    assert protocol.stages == (
        PriorArtStage.QUERY_LATTICE,
        PriorArtStage.LITERAL_SEARCH,
        PriorArtStage.SYNONYM_SEARCH,
        PriorArtStage.SEMANTIC_SEARCH,
        PriorArtStage.CLASSIFICATION_SEARCH,
        PriorArtStage.MULTILINGUAL_SEARCH,
        PriorArtStage.PATENT_SCOUT,
        PriorArtStage.SCIENCE_SCOUT,
        PriorArtStage.CODE_SCOUT,
        PriorArtStage.PRODUCT_SCOUT,
        PriorArtStage.CROSS_DOMAIN_SCOUT,
        PriorArtStage.SKEPTIC,
        PriorArtStage.VERDICT,
    )
    assert protocol.can_execute(rounds_completed=1, mutations_completed=1)
    assert not protocol.can_execute(rounds_completed=2, mutations_completed=0)
    assert not protocol.can_mutate(mutations_completed=2)
    assert "PROVEN_NEW" not in protocol.allowed_verdicts

    with pytest.raises(ValueError, match="max_prior_art_rounds"):
        AdversarialSearchProtocol(candidate_id="cand_001", max_prior_art_rounds=0)


def test_adversarial_protocol_allows_initial_search_without_mutation_budget():
    protocol = AdversarialSearchProtocol(
        candidate_id="cand_001",
        max_prior_art_rounds=1,
        max_mutations_per_candidate=0,
    )

    assert protocol.can_execute(rounds_completed=0, mutations_completed=0)
    assert not protocol.can_mutate(mutations_completed=0)


def test_query_lattice_adds_traceable_classification_variants_deterministically():
    first = build_query_lattice(
        "cooling energy",
        classifications=["Y02E", "F25B", "Y02E"],
        max_variants=20,
    )
    second = build_query_lattice(
        "cooling energy",
        classifications=["F25B", "Y02E"],
        max_variants=20,
    )

    assert [(variant.text, variant.language, variant.origin, variant.technique_ids) for variant in first] == [
        (variant.text, variant.language, variant.origin, variant.technique_ids) for variant in second
    ]
    assert first[0].text == "cooling energy"
    assert first[0].origin == "original"
    assert [
        (variant.text, variant.origin, variant.technique_ids)
        for variant in first
        if variant.origin == "classification"
    ] == [
        ("F25B cooling energy", "classification", ("T003",)),
        ("Y02E cooling energy", "classification", ("T003",)),
    ]
    assert len({(variant.text, variant.language) for variant in first}) == len(first)
