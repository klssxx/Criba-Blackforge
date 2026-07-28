"""Tests for constraints.py — HIPERMEGAPROMPT §4."""
from __future__ import annotations

import pytest
from criba.constraints import (
    KnowledgeStatus,
    NoveltyStatus,
    FindingConfidence,
    ConstraintSet,
    ConstraintViolation,
    ConstraintValidation,
    classify_knowledge,
    classify_novelty,
    build_constraints,
    validate_idea_against_constraints,
)


# ---------------------------------------------------------------------------
# KnowledgeStatus
# ---------------------------------------------------------------------------

class TestKnowledgeStatus:
    def test_all_values(self) -> None:
        assert len(KnowledgeStatus) == 6

    def test_values(self) -> None:
        expected = {"confirmed_fact", "source_supported", "inference",
                    "assumption", "speculation", "unknown"}
        assert {s.value for s in KnowledgeStatus} == expected


# ---------------------------------------------------------------------------
# classify_knowledge
# ---------------------------------------------------------------------------

class TestClassifyKnowledge:
    def test_speculation(self) -> None:
        assert classify_knowledge("Inventado por mí") == KnowledgeStatus.SPECULATION

    def test_unknown(self) -> None:
        assert classify_knowledge("No sé nada de esto") == KnowledgeStatus.UNKNOWN

    def test_confirmed_with_sources(self) -> None:
        assert classify_knowledge(
            "Demostrado experimentalmente", sources=["paper1.pdf"]
        ) == KnowledgeStatus.CONFIRMED_FACT

    def test_source_supported(self) -> None:
        assert classify_knowledge(
            "Según el informe", sources=["report.pdf"]
        ) == KnowledgeStatus.SOURCE_SUPPORTED

    def test_inference_with_sources(self) -> None:
        assert classify_knowledge(
            "Probablemente funciona", sources=["data.csv"]
        ) == KnowledgeStatus.INFERENCE

    def test_assumption_without_sources(self) -> None:
        assert classify_knowledge("Asumimos que funciona") == KnowledgeStatus.ASSUMPTION


# ---------------------------------------------------------------------------
# classify_novelty
# ---------------------------------------------------------------------------

class TestClassifyNovelty:
    def test_known(self) -> None:
        assert classify_novelty(
            "Usar WAF para proteger API", known_solutions=["WAF"]
        ) == NoveltyStatus.KNOWN

    def test_incremental(self) -> None:
        assert classify_novelty("Mejorar ligeramente el algoritmo") == NoveltyStatus.INCREMENTAL

    def test_uncommon_combination(self) -> None:
        assert classify_novelty("Combinación de biometría y blockchain") == NoveltyStatus.UNCOMMON_COMBINATION

    def test_unverified(self) -> None:
        assert classify_novelty("Nunca se ha hecho antes") == NoveltyStatus.UNVERIFIED_NOVELTY

    def test_potentially_novel_default(self) -> None:
        assert classify_novelty("Algo completamente diferente") == NoveltyStatus.POTENTIALLY_NOVEL


# ---------------------------------------------------------------------------
# ConstraintSet
# ---------------------------------------------------------------------------

class TestConstraintSet:
    def test_criba_defaults(self) -> None:
        cs = ConstraintSet()
        assert cs.no_invent_information is True
        assert cs.no_ideas_without_mechanism is True
        assert cs.require_authorization is False

    def test_blackforge_defaults(self) -> None:
        cs = ConstraintSet(
            require_authorization=True,
            require_bypass_analysis=True,
            require_residual_risk=True,
        )
        assert cs.require_authorization is True
        assert cs.require_bypass_analysis is True


# ---------------------------------------------------------------------------
# build_constraints
# ---------------------------------------------------------------------------

class TestBuildConstraints:
    def test_criba_mode(self) -> None:
        cs = build_constraints(mode="criba")
        assert cs.require_authorization is False
        assert cs.no_invent_information is True

    def test_blackforge_mode(self) -> None:
        cs = build_constraints(mode="blackforge")
        assert cs.require_authorization is True
        assert cs.require_bypass_analysis is True
        assert cs.require_residual_risk is True

    def test_unknown_mode_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown mode"):
            build_constraints(mode="invalid")

    def test_extra_constraints_from_context(self) -> None:
        ctx = {"constraints": ["Budget < 10k", "No PII allowed"]}
        cs = build_constraints(context=ctx)
        assert "Budget < 10k" in cs.extra_constraints


# ---------------------------------------------------------------------------
# validate_idea_against_constraints
# ---------------------------------------------------------------------------

class TestValidateIdea:
    def test_valid_idea(self) -> None:
        idea = {
            "title": "WAF with ML rules",
            "mechanism": "Deploy ML-based WAF that adapts rules dynamically",
            "problem_anchor": "Static WAF rules fail against novel attacks",
            "risks": ["Model drift", "False positives"],
        }
        cs = ConstraintSet()
        result = validate_idea_against_constraints(idea, cs, "criba")
        assert result.passes
        assert len(result.violations) == 0

    def test_no_mechanism_rejected(self) -> None:
        idea = {"title": "Use AI", "mechanism": "usar ia"}
        cs = ConstraintSet()
        result = validate_idea_against_constraints(idea, cs, "criba")
        assert not result.passes
        assert any("no_ideas_without_mechanism" in v.rule for v in result.violations)

    def test_empty_mechanism_rejected(self) -> None:
        idea = {"title": "Idea", "mechanism": ""}
        cs = ConstraintSet()
        result = validate_idea_against_constraints(idea, cs, "criba")
        assert not result.passes

    def test_no_risks_warning(self) -> None:
        idea = {
            "title": "Good idea",
            "mechanism": "Specific technical mechanism with clear steps",
        }
        cs = ConstraintSet()
        result = validate_idea_against_constraints(idea, cs, "criba")
        assert result.passes  # warnings don't fail
        assert any("risks" in w.lower() for w in result.warnings)

    def test_blackforge_auth_required(self) -> None:
        idea = {
            "title": "Pentest API",
            "mechanism": "SQL injection test",
        }
        cs = build_constraints(mode="blackforge")
        result = validate_idea_against_constraints(idea, cs, "blackforge")
        assert not result.passes
        assert any("authorization" in v.rule for v in result.violations)

    def test_blackforge_with_auth_passes(self) -> None:
        idea = {
            "title": "Pentest API",
            "mechanism": "SQL injection test on staging environment",
            "authorization_status": "authorized by CISO",
            "bypass": "Rate limiting may block attempts",
            "residual_risk": "Low - staging only",
        }
        cs = build_constraints(mode="blackforge")
        result = validate_idea_against_constraints(idea, cs, "blackforge")
        assert result.passes

    def test_unknown_mode_raises(self) -> None:
        idea = {"title": "test", "mechanism": "test"}
        cs = ConstraintSet()
        with pytest.raises(ValueError, match="Unknown mode"):
            validate_idea_against_constraints(idea, cs, "invalid")
