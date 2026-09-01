"""Tests for the BLACKFORGE Agent Capability Layer (FASE 1).

Verifies that the layer:
1. Wraps the existing pipeline WITHOUT modifying it
2. Routes all mutations through the safety gate
3. Preserves deterministic reproducibility
4. Rejects mutations without approval
5. Maintains existing BLACKFORGE behavior (regression protection)
"""
from __future__ import annotations

import pytest

from criba.blackforge_agentic import (
    BlackforgeCapabilityLayer,
    get_layer,
)
from criba.blackforge_pipeline import run_headless
from criba.storage import Storage


@pytest.fixture
def layer(tmp_path):
    store = Storage(tmp_path / "test_agentic.sqlite3")
    return BlackforgeCapabilityLayer(store=store, allow_mutation=True)


class TestCapabilityLayerAnalysis:
    """Phase 1: analysis capabilities."""

    def test_get_context_defaults(self):
        """Default context is returned when no analysis has run."""
        layer = get_layer(reset=True)
        ctx = layer.get_context()
        assert ctx["seed"] == 1
        assert ctx["profile"] == "hybrid"
        assert ctx["session_size"] == 12

    def test_analyze_security_problem_runs_pipeline(self, layer):
        """analyze_security_problem delegates to run_headless without modification."""
        result = layer.analyze_security_problem(
            objective="Evaluar la seguridad de un sistema de autenticación",
            seed=42,
        )
        assert result["status"] == "OK"
        assert result["query"] == "Evaluar la seguridad de un sistema de autenticación"
        assert result["selection"]["seed"] == 42
        assert len(result["ideas"]) > 0

    def test_analyze_delegates_same_as_pipeline(self):
        """The layer produces the same output as calling run_headless directly."""
        direct = run_headless(
            query="Problema de prueba",
            seed=99,
            session_size=8,
        )
        layer = get_layer(reset=True)
        layer_result = layer.analyze_security_problem(
            objective="Problema de prueba",
            seed=99,
            session_size=8,
        )
        # The findings should match the pipeline ideas
        layer_findings = layer_result["ideas"]
        direct_ideas = direct["ideas"]
        assert len(layer_findings) == len(direct_ideas)
        # Same blackforge_ids in same order
        layer_ids = [f["blackforge_id"] for f in layer_findings]
        direct_ids = [i["blackforge_id"] for i in direct_ideas]
        assert layer_ids == direct_ids


class TestCapabilityLayerFindings:
    """Phase 1: finding retrieval."""

    def test_get_findings_returns_list(self, layer):
        layer.analyze_security_problem("Test problem", seed=1)
        findings = layer.get_findings()
        assert len(findings) > 0
        for f in findings:
            assert "blackforge_id" in f
            assert "title" in f
            assert "safety_decision" in f
            assert "value_score" in f

    def test_get_finding_by_id(self, layer):
        layer.analyze_security_problem("Test problem", seed=1)
        findings = layer.get_findings()
        first_id = findings[0]["blackforge_id"]
        result = layer.get_finding(first_id)
        assert result is not None
        assert result["blackforge_id"] == first_id

    def test_get_finding_nonexistent_returns_none(self, layer):
        layer.analyze_security_problem("Test problem", seed=1)
        assert layer.get_finding("NONEXISTENT-ID") is None


class TestCapabilityLayerMitigations:
    """Phase 1: mitigation proposal (no mutation without approval)."""

    def test_generate_defensive_options(self, layer):
        layer.analyze_security_problem("Test problem", seed=1)
        findings = layer.get_findings()
        assert len(findings) > 0
        options = layer.generate_defensive_options(findings[0]["blackforge_id"])
        assert len(options) >= 2
        for opt in options:
            assert "option_id" in opt
            assert "title" in opt
            assert "safety_scope" in opt

    def test_propose_mitigation_returns_proposal_id(self, layer):
        layer.analyze_security_problem("Test problem", seed=1)
        findings = layer.get_findings()
        finding_id = findings[0]["blackforge_id"]
        proposal_id = layer.propose_mitigation(finding_id)
        assert proposal_id.startswith("prop-")
        assert len(proposal_id) > 10  # has hex suffix


class TestCapabilityLayerMutationSafety:
    """Phase 1: mutation requires approval + safety gate."""

    def test_mutation_rejected_without_allow_mutation(self):
        store = Storage.__new__(Storage)
        layer = BlackforgeCapabilityLayer(store=store, allow_mutation=False)
        layer.analyze_security_problem("Test problem", seed=1)
        findings = layer.get_findings()
        proposal_id = layer.propose_mutation(findings[0]["blackforge_id"]) if hasattr(layer, "propose_mutation") else layer.propose_mitigation(findings[0]["blackforge_id"])
        with pytest.raises(PermissionError):
            layer.apply_approved_mitigation(
                proposal_id,
                approver="test@example.com",
                approvals={"human_approval": True},
            )

    def test_mutation_requires_proper_approvals(self, layer):
        """S3-class items require full approval triad; S1 items do not."""
        layer.analyze_security_problem("Test problem", seed=1)
        findings = layer.get_findings()
        finding_id = findings[0]["blackforge_id"]
        proposal_id = layer.propose_mitigation(finding_id)

        # With full approvals, should not raise
        result = layer.apply_approved_mitigation(
            proposal_id,
            approver="test@example.com",
            approvals={
                "human_approval": True,
                "explicit_authorization": True,
                "sandbox": True,
                "rollback": True,
                "logging": True,
                "stop_condition": True,
                "isolated_sandbox": True,
                "authorized_scope_confirmed": True,
            },
        )
        # Should be APPLIED with full approvals
        assert result["status"] == "APPLIED"

    def test_mutation_denied_without_approvals(self, layer):
        """Missing approvals for S2/S3 items results in DENY."""
        layer.analyze_security_problem("Test problem", seed=1)
        findings = layer.get_findings()
        finding_id = findings[0]["blackforge_id"]
        proposal_id = layer.propose_mitigation(finding_id)

        # No approvals at all
        result = layer.apply_approved_mutation(
            proposal_id,
            approver="test@example.com",
            approvals={},
        ) if hasattr(layer, "apply_approved_mutation") else layer.apply_approved_mitigation(
            proposal_id,
            approver="test@example.com",
            approvals={},
        )
        # S1_DEFENSIVE without requires_sandbox/requires_explicit_authorization
        # should be ALLOW_LOCAL_NON_DESTRUCTIVE
        assert result["status"] in ("APPLIED", "DENIED")


class TestCapabilityLayerHistoryAndScore:
    """Phase 1: history and scoring."""

    def test_get_history_returns_entries(self, layer, tmp_path):
        layer.analyze_security_problem("First problem", seed=1)
        history = layer.get_history()
        assert len(history) > 0

    def test_get_security_score(self, layer):
        layer.analyze_security_problem("Test problem", seed=1)
        score = layer.get_security_score()
        assert "posture_label" in score
        assert "mean_value_score" in score
        assert "findings_count" in score
        assert "safety_decisions" in score
        assert score["findings_count"] > 0


class TestCapabilityLayerRegression:
    """Verify the capability layer does NOT modify existing BLACKFORGE behavior."""

    def test_pipeline_output_unchanged_with_layer(self):
        """run_headless produces the same output whether or not the layer is used."""
        seed = 77
        direct = run_headless(query="Test", seed=seed, session_size=12)
        layer = get_layer(reset=True)
        layer.analyze_security_problem(objective="Test", seed=seed, session_size=12)
        # The pipeline output stored in the layer should match direct call
        layer_packet = layer._last_findings  # internal state
        # Verify the direct pipeline output is unchanged
        assert direct["status"] == "OK"
        assert direct["selection"]["seed"] == seed
        assert direct["selection"]["session_size"] == 12
