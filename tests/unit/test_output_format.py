"""Tests for output_format.py — HIPERMEGAPROMPT §5."""
from __future__ import annotations

from criba.output_format import (
    MAX_FULLY_DEVELOPED_IDEAS,
    MAX_PRIMARY_RECOMMENDATIONS,
    MAX_SECONDARY_ALTERNATIVES,
    AuthorizationRecord,
    BlackforgeOutput,
    BlackforgeRankingRow,
    CribaOutput,
    DecisionRecord,
    ExecutiveSummary,
    FindingRow,
    IdeaOutput,
    InterpretedContext,
    KnownSpace,
    OperatorRow,
    RankingRow,
    SecuritySummary,
    ThreatModel,
    format_blackforge_output,
    format_criba_output,
    validate_output_limits,
)

# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------

class TestLimits:
    def test_max_primary(self) -> None:
        assert MAX_PRIMARY_RECOMMENDATIONS == 1

    def test_max_alternatives(self) -> None:
        assert MAX_SECONDARY_ALTERNATIVES == 3

    def test_max_ideas(self) -> None:
        assert MAX_FULLY_DEVELOPED_IDEAS == 5


# ---------------------------------------------------------------------------
# CribaOutput
# ---------------------------------------------------------------------------

class TestCribaOutput:
    def test_defaults(self) -> None:
        out = CribaOutput()
        assert out.ideas == []
        assert out.ranking == []
        assert isinstance(out.executive_summary, ExecutiveSummary)

    def test_idea_limit_enforced(self) -> None:
        ideas = [IdeaOutput(id=str(i), title=f"Idea {i}") for i in range(10)]
        out = CribaOutput(ideas=ideas)
        # Limit is enforced by validate_output_limits(), not by truncation
        result = validate_output_limits(out)
        assert not result.is_valid
        assert len(out.ideas) == 10  # raw count preserved

    def test_serialization_roundtrip(self) -> None:
        out = CribaOutput(
            executive_summary=ExecutiveSummary(problem="test", recommended_idea="Idea A"),
            ideas=[IdeaOutput(id="1", title="Idea A", mechanism="specific mechanism")],
        )
        data = out.model_dump()
        restored = CribaOutput(**data)
        assert restored.executive_summary.problem == "test"
        assert len(restored.ideas) == 1

    def test_interpreted_context(self) -> None:
        ctx = InterpretedContext(
            original_query="test",
            domain="seguridad",
            actors=["attacker"],
        )
        out = CribaOutput(interpreted_context=ctx)
        assert out.interpreted_context.domain == "seguridad"

    def test_known_space(self) -> None:
        ks = KnownSpace(
            existing_solutions=["WAF"],
            dominant_paradigms=["perimeter security"],
        )
        out = CribaOutput(known_space=ks)
        assert "WAF" in out.known_space.existing_solutions

    def test_operators_table(self) -> None:
        ops = [OperatorRow(operator="invert", motivo="Break assumption", element_transformed="defense model")]
        out = CribaOutput(operators=ops)
        assert len(out.operators) == 1
        assert out.operators[0].operator == "invert"


# ---------------------------------------------------------------------------
# BlackforgeOutput
# ---------------------------------------------------------------------------

class TestBlackforgeOutput:
    def test_defaults(self) -> None:
        out = BlackforgeOutput()
        assert isinstance(out.security_summary, SecuritySummary)
        assert isinstance(out.authorization, AuthorizationRecord)
        assert isinstance(out.threat_model, ThreatModel)
        assert isinstance(out.decision, DecisionRecord)

    def test_full_construction(self) -> None:
        out = BlackforgeOutput(
            security_summary=SecuritySummary(
                protected_asset="API",
                threat="SQL injection",
                proposed_mechanism="Input validation",
            ),
            authorization=AuthorizationRecord(status="authorized", scope="lab"),
            threat_model=ThreatModel(
                assets=["API"],
                threat_actors=["external"],
            ),
            findings=[
                FindingRow(severity="HIGH", finding="SQLi in login", evidence="PoC"),
            ],
            ranking=[
                BlackforgeRankingRow(position=1, proposal="Input validation"),
            ],
            decision=DecisionRecord(status="recommended", reason="Mitigates SQLi"),
        )
        assert out.security_summary.protected_asset == "API"
        assert out.authorization.status == "authorized"
        assert len(out.findings) == 1
        assert out.decision.status == "recommended"

    def test_serialization_roundtrip(self) -> None:
        out = BlackforgeOutput(
            security_summary=SecuritySummary(threat="XSS"),
            decision=DecisionRecord(status="recommended"),
        )
        data = out.model_dump()
        restored = BlackforgeOutput(**data)
        assert restored.security_summary.threat == "XSS"


# ---------------------------------------------------------------------------
# format_criba_output
# ---------------------------------------------------------------------------

class TestFormatCribaOutput:
    def test_empty_inputs(self) -> None:
        out = format_criba_output()
        assert isinstance(out, CribaOutput)
        assert out.ideas == []

    def test_with_context_and_ideas(self) -> None:
        ctx = {
            "original_query": "test",
            "central_problem": "the problem",
            "primary_domain": "tecnologia",
            "actors": ["users"],
            "assumptions": ["a1"],
            "known_solutions": ["s1"],
        }
        ideas = [
            {"id": "1", "title": "Idea A", "mechanism": "Mech A", "principal_risk": "risk1"},
            {"id": "2", "title": "Idea B", "mechanism": "Mech B"},
        ]
        ranking = [
            {"id": "1", "title": "Idea A", "value_score": 0.8},
            {"id": "2", "title": "Idea B", "value_score": 0.6},
        ]
        out = format_criba_output(context=ctx, ideas=ideas, ranking=ranking)
        assert out.executive_summary.problem == "the problem"
        assert out.interpreted_context.domain == "tecnologia"
        assert len(out.ideas) == 2
        assert len(out.ranking) == 2

    def test_discarded_ideas(self) -> None:
        ideas = [{"id": str(i), "title": f"Idea {i}", "mechanism": f"Mech {i}"} for i in range(8)]
        out = format_criba_output(ideas=ideas)
        assert len(out.ideas) == MAX_FULLY_DEVELOPED_IDEAS
        assert len(out.discarded) == 3


# ---------------------------------------------------------------------------
# format_blackforge_output
# ---------------------------------------------------------------------------

class TestFormatBlackforgeOutput:
    def test_empty_inputs(self) -> None:
        out = format_blackforge_output()
        assert isinstance(out, BlackforgeOutput)

    def test_with_context(self) -> None:
        ctx = {
            "protected_assets": ["API"],
            "threat_actors": ["attacker"],
            "authorization_state": "authorized",
        }
        out = format_blackforge_output(context=ctx)
        assert out.threat_model.assets == ["API"]
        assert out.authorization.status == "authorized"


# ---------------------------------------------------------------------------
# validate_output_limits
# ---------------------------------------------------------------------------

class TestValidateOutputLimits:
    def test_valid_criba(self) -> None:
        out = CribaOutput(
            ideas=[IdeaOutput(id=str(i), title=f"I {i}") for i in range(3)],
            ranking=[RankingRow(position=i, idea_id=str(i), idea_title=f"I {i}") for i in range(2)],
        )
        result = validate_output_limits(out)
        assert result.is_valid

    def test_too_many_ideas(self) -> None:
        out = CribaOutput(
            ideas=[IdeaOutput(id=str(i), title=f"I {i}") for i in range(10)],
        )
        result = validate_output_limits(out)
        assert not result.is_valid
        assert any("10" in v for v in result.violations)

    def test_valid_blackforge(self) -> None:
        out = BlackforgeOutput(
            findings=[FindingRow(finding=f"F{i}") for i in range(3)],
        )
        result = validate_output_limits(out)
        assert result.is_valid
