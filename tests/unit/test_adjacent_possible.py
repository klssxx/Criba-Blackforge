"""Unit tests for Adjacent Possible & Falsification Governor."""
from __future__ import annotations

from criba.core.adjacent_possible import AdjacentPossibleGovernor


def test_adjacent_possible_accepts_novel_breakthrough() -> None:
    gov = AdjacentPossibleGovernor()
    res = gov.evaluate_proposal(
        proposal_id="prop-breakthrough-01",
        target_axiom="Static network perimeter inspection",
        intervention="Causal Entropy Dynamic Memory Mutator",
        causal_axes_moved=["topologia", "aislamiento_memoria", "trust_model"],
        domain="cybersecurity"
    )

    assert res.is_valid_adjacent_possible is True
    assert 0.45 <= res.adjacent_distance <= 0.85
    assert len(res.sota_taboo_violations) == 0
    assert "H0:" in res.null_hypothesis_h0
    assert res.containment_class in ["S1_DEFENSIVE", "S2_SANDBOX"]


def test_adjacent_possible_rejects_sota_taboo_cliche() -> None:
    gov = AdjacentPossibleGovernor()
    res = gov.evaluate_proposal(
        proposal_id="prop-cliche-01",
        target_axiom="Network security",
        intervention="static_firewall with port_blocking",
        causal_axes_moved=[],
        domain="cybersecurity"
    )

    assert res.is_valid_adjacent_possible is False
    assert len(res.sota_taboo_violations) > 0
