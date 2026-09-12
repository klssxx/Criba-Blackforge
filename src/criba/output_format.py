"""Output Format Layer — Structured output contracts (HIPERMEGAPROMPT §5).

Defines the canonical output schemas for CRIBA and Blackforge results,
including ranking, limits, and traceability.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Output limits (§5.5)
# ---------------------------------------------------------------------------

MAX_PRIMARY_RECOMMENDATIONS = 1
MAX_SECONDARY_ALTERNATIVES = 3
MAX_FULLY_DEVELOPED_IDEAS = 5


# ---------------------------------------------------------------------------
# CRIBA output components
# ---------------------------------------------------------------------------

class ExecutiveSummary(BaseModel):
    """§5.2 — Resumen ejecutivo."""

    problem: str = ""
    main_finding: str = ""
    recommended_idea: str = ""
    why_it_wins: str = ""
    principal_risk: str = ""
    next_validation: str = ""


class InterpretedContext(BaseModel):
    """§5.2 — Contexto interpretado."""

    original_query: str = ""
    central_problem: str = ""
    desired_outcome: str = ""
    domain: str = ""
    actors: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)


class KnownSpace(BaseModel):
    """§5.2 — Espacio conocido."""

    existing_solutions: list[str] = Field(default_factory=list)
    dominant_paradigms: list[str] = Field(default_factory=list)
    known_failures: list[str] = Field(default_factory=list)
    unresolved_gaps: list[str] = Field(default_factory=list)
    assumptions_to_break: list[str] = Field(default_factory=list)


class OperatorRow(BaseModel):
    """Single row in the operators table."""

    operator: str
    motivo: str
    element_transformed: str


class IdeaOutput(BaseModel):
    """§5.2 — Single idea with all required fields."""

    id: str = ""
    title: str = ""
    one_sentence_description: str = ""
    problem_anchor: str = ""
    mechanism: str = ""
    operator_used: str = ""
    novelty: str = ""
    expected_value: str = ""
    implementation_requirements: str = ""
    principal_risk: str = ""
    validation_method: str = ""


class RankingRow(BaseModel):
    """Single row in the ranking table."""

    position: int
    idea_id: str
    idea_title: str
    value: float = 0.0
    novelty: float = 0.0
    feasibility: float = 0.0
    risk: float = 0.0
    final: float = 0.0


class WinningProposal(BaseModel):
    """§5.2 — Ganadora."""

    title: str = ""
    central_mechanism: str = ""
    why_it_wins: str = ""
    expected_impact: str = ""
    dependencies: list[str] = Field(default_factory=list)
    implementation_path: str = ""
    failure_conditions: list[str] = Field(default_factory=list)
    evidence_needed: list[str] = Field(default_factory=list)


class CribaOutput(BaseModel):
    """Complete CRIBA output contract (§5.2)."""

    executive_summary: ExecutiveSummary = Field(default_factory=ExecutiveSummary)
    interpreted_context: InterpretedContext = Field(default_factory=InterpretedContext)
    known_space: KnownSpace = Field(default_factory=KnownSpace)
    operators: list[OperatorRow] = Field(default_factory=list)
    ideas: list[IdeaOutput] = Field(default_factory=list)
    ranking: list[RankingRow] = Field(default_factory=list)
    winning_proposal: WinningProposal = Field(default_factory=WinningProposal)
    discarded: list[dict[str, Any]] = Field(default_factory=list)
    next_step: str = ""


# ---------------------------------------------------------------------------
# Blackforge output components
# ---------------------------------------------------------------------------

class SecuritySummary(BaseModel):
    """§5.3 — Resumen de seguridad."""

    protected_asset: str = ""
    threat: str = ""
    main_weakness: str = ""
    proposed_mechanism: str = ""
    expected_security_gain: str = ""
    principal_bypass: str = ""
    residual_risk: str = ""
    validation_environment: str = ""


class AuthorizationRecord(BaseModel):
    """§5.3 — Autorización."""

    status: str = "unauthorized"
    owner: str = ""
    environment: str = ""
    scope: str = ""
    allowed_actions: list[str] = Field(default_factory=list)
    prohibited_actions: list[str] = Field(default_factory=list)
    stop_conditions: list[str] = Field(default_factory=list)


class ThreatModel(BaseModel):
    """§5.3 — Threat model."""

    assets: list[str] = Field(default_factory=list)
    threat_actors: list[str] = Field(default_factory=list)
    attacker_goals: list[str] = Field(default_factory=list)
    attacker_capabilities: list[str] = Field(default_factory=list)
    entry_vectors: list[str] = Field(default_factory=list)
    trust_boundaries: list[str] = Field(default_factory=list)
    attack_paths: list[str] = Field(default_factory=list)
    existing_controls: list[str] = Field(default_factory=list)
    control_gaps: list[str] = Field(default_factory=list)


class OffensiveHypothesis(BaseModel):
    """§5.3 — Hipótesis ofensiva."""

    hypothesis: str = ""
    preconditions: list[str] = Field(default_factory=list)
    affected_component: str = ""
    expected_behavior: str = ""
    insecure_behavior: str = ""
    evidence_required: list[str] = Field(default_factory=list)
    safe_validation: str = ""


class DefensiveMechanism(BaseModel):
    """§5.3 — Mecanismo defensivo."""

    protected_property: str = ""
    mechanism: str = ""
    attacker_capability_removed: str = ""
    defender_capability_added: str = ""
    dependencies: list[str] = Field(default_factory=list)
    telemetry: str = ""
    containment: str = ""
    recovery: str = ""


class AdversarialReview(BaseModel):
    """§5.3 — Revisión adversarial."""

    likely_bypass: str = ""
    alternate_attack_path: str = ""
    trusted_component_failure: str = ""
    operational_failure: str = ""
    detection_gap: str = ""
    abuse_potential: str = ""


class EvidenceRecord(BaseModel):
    """§5.3 — Evidencia."""

    confirmed: list[str] = Field(default_factory=list)
    observed: list[str] = Field(default_factory=list)
    inferred: list[str] = Field(default_factory=list)
    assumed: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)


class FindingRow(BaseModel):
    """Single row in the findings table."""

    severity: str = ""
    finding: str = ""
    evidence: str = ""
    impact: str = ""
    root_cause: str = ""
    remediation: str = ""


class BlackforgeRankingRow(BaseModel):
    """Single row in the Blackforge ranking table."""

    position: int
    proposal: str
    defensive_impact: float = 0.0
    bypass: float = 0.0
    verifiability: float = 0.0
    feasibility: float = 0.0
    residual_risk: float = 0.0


class BlackforgeWinner(BaseModel):
    """§5.3 — Ganadora Blackforge."""

    name: str = ""
    security_problem: str = ""
    technical_mechanism: str = ""
    protected_assets: list[str] = Field(default_factory=list)
    threat_actor: str = ""
    attack_surface: str = ""
    security_property: str = ""
    offensive_hypothesis: str = ""
    defensive_response: str = ""
    validation_plan: str = ""
    expected_evidence: list[str] = Field(default_factory=list)
    likely_bypass: str = ""
    residual_risk: str = ""
    implementation_cost: str = ""
    why_it_wins: str = ""


class ValidationPlanRecord(BaseModel):
    """§5.3 — Plan de validación segura."""

    environment: str = ""
    preconditions: list[str] = Field(default_factory=list)
    test_data: str = ""
    actions: list[str] = Field(default_factory=list)
    expected_secure_result: str = ""
    failure_indicator: str = ""
    evidence_to_collect: list[str] = Field(default_factory=list)
    stop_conditions: list[str] = Field(default_factory=list)
    rollback: str = ""
    retest: str = ""


class DecisionRecord(BaseModel):
    """§5.3 — Decisión."""

    status: str = "insufficient_evidence"
    reason: str = ""
    blocking_risks: list[str] = Field(default_factory=list)
    next_action: str = ""


class BlackforgeOutput(BaseModel):
    """Complete Blackforge output contract (§5.3)."""

    security_summary: SecuritySummary = Field(default_factory=SecuritySummary)
    authorization: AuthorizationRecord = Field(default_factory=AuthorizationRecord)
    threat_model: ThreatModel = Field(default_factory=ThreatModel)
    offensive_hypothesis: OffensiveHypothesis = Field(default_factory=OffensiveHypothesis)
    defensive_mechanism: DefensiveMechanism = Field(default_factory=DefensiveMechanism)
    adversarial_review: AdversarialReview = Field(default_factory=AdversarialReview)
    evidence: EvidenceRecord = Field(default_factory=EvidenceRecord)
    findings: list[FindingRow] = Field(default_factory=list)
    ranking: list[BlackforgeRankingRow] = Field(default_factory=list)
    winner: BlackforgeWinner = Field(default_factory=BlackforgeWinner)
    validation_plan: ValidationPlanRecord = Field(default_factory=ValidationPlanRecord)
    decision: DecisionRecord = Field(default_factory=DecisionRecord)


# ---------------------------------------------------------------------------
# Format builders
# ---------------------------------------------------------------------------

def format_criba_output(
    context: dict[str, Any] | None = None,
    ideas: list[dict[str, Any]] | None = None,
    ranking: list[dict[str, Any]] | None = None,
) -> CribaOutput:
    """Build a CribaOutput from engine results (§5.2).

    Parameters
    ----------
    context : dict, optional
        InnovationContext as dict.
    ideas : list[dict], optional
        Generated ideas.
    ranking : list[dict], optional
        Ranked ideas with scores.
    """
    ctx = context or {}
    ideas_list = ideas or []
    ranking_list = ranking or []

    # Executive summary from top idea
    top = ideas_list[0] if ideas_list else {}
    summary = ExecutiveSummary(
        problem=ctx.get("central_problem", ""),
        main_finding=top.get("title", ""),
        recommended_idea=top.get("title", ""),
        why_it_wins=top.get("mechanism", ""),
        principal_risk=top.get("principal_risk", top.get("risks", "")),
        next_validation=top.get("validation_method", ""),
    )

    # Interpreted context
    interp = InterpretedContext(
        original_query=ctx.get("original_query", ""),
        central_problem=ctx.get("central_problem", ""),
        desired_outcome=ctx.get("desired_outcome", ""),
        domain=ctx.get("primary_domain", ""),
        actors=ctx.get("actors", []),
        constraints=ctx.get("constraints", []),
        assumptions=ctx.get("assumptions", []),
        unknowns=ctx.get("unknowns", []),
    )

    # Known space
    known = KnownSpace(
        existing_solutions=ctx.get("known_solutions", []),
        dominant_paradigms=ctx.get("dominant_paradigms", []),
        known_failures=ctx.get("known_failures", []),
        assumptions_to_break=ctx.get("assumptions", []),
    )

    # Ideas (limited)
    idea_outputs = []
    for i in ideas_list[:MAX_FULLY_DEVELOPED_IDEAS]:
        idea_outputs.append(IdeaOutput(
            id=i.get("id", ""),
            title=i.get("title", ""),
            one_sentence_description=i.get("description", i.get("one_sentence_description", "")),
            problem_anchor=i.get("problem_anchor", ""),
            mechanism=i.get("mechanism", ""),
            operator_used=i.get("operator_used", i.get("method_applied", "")),
            novelty=i.get("novelty", ""),
            expected_value=str(i.get("expected_value", "")),
            implementation_requirements=i.get("implementation_requirements", ""),
            principal_risk=i.get("principal_risk", i.get("risks", "")),
            validation_method=i.get("validation_method", ""),
        ))

    # Ranking
    rank_rows = []
    for idx, r in enumerate(ranking_list[:MAX_FULLY_DEVELOPED_IDEAS]):
        rank_rows.append(RankingRow(
            position=idx + 1,
            idea_id=r.get("id", r.get("idea_id", "")),
            idea_title=r.get("title", r.get("idea_title", "")),
            value=r.get("value", r.get("value_score", 0.0)),
            novelty=r.get("novelty", 0.0),
            feasibility=r.get("feasibility", 0.0),
            risk=r.get("risk", 0.0),
            final=r.get("final", 0.0),
        ))

    # Winner
    winner = WinningProposal(
        title=top.get("title", ""),
        central_mechanism=top.get("mechanism", ""),
        why_it_wins=top.get("one_sentence_description", ""),
        expected_impact=top.get("expected_value", ""),
        implementation_path=top.get("implementation_requirements", ""),
    )

    # Discarded (ideas beyond the limit)
    discarded = []
    for i in ideas_list[MAX_FULLY_DEVELOPED_IDEAS:]:
        discarded.append({
            "id": i.get("id", ""),
            "title": i.get("title", ""),
            "reason": "Exceeded output limit",
        })

    return CribaOutput(
        executive_summary=summary,
        interpreted_context=interp,
        known_space=known,
        ideas=idea_outputs,
        ranking=rank_rows,
        winning_proposal=winner,
        discarded=discarded,
        next_step="Validar propuesta ganadora con prototipo o experimento controlado",
    )


def format_blackforge_output(
    context: dict[str, Any] | None = None,
    ideas: list[dict[str, Any]] | None = None,
    ranking: list[dict[str, Any]] | None = None,
) -> BlackforgeOutput:
    """Build a BlackforgeOutput from security analysis results (§5.3).

    Parameters
    ----------
    context : dict, optional
        BlackforgeContext as dict.
    ideas : list[dict], optional
        Generated security ideas/proposals.
    ranking : list[dict], optional
        Ranked proposals.
    """
    ctx = context or {}
    ideas_list = ideas or []
    ranking_list = ranking or []
    top = ideas_list[0] if ideas_list else {}

    sec_summary = SecuritySummary(
        protected_asset=top.get("protected_asset", ""),
        threat=top.get("threat", ""),
        main_weakness=top.get("main_weakness", top.get("weakness", "")),
        proposed_mechanism=top.get("mechanism", top.get("defensive_mechanism", "")),
        expected_security_gain=top.get("expected_security_gain", ""),
        principal_bypass=top.get("bypass", top.get("principal_bypass", "")),
        residual_risk=top.get("residual_risk", ""),
        validation_environment=top.get("validation_environment", "laboratorio aislado"),
    )

    authorization = AuthorizationRecord(
        status=ctx.get("authorization_state", "unauthorized"),
        owner=ctx.get("authorization_owner", ""),
        environment=ctx.get("authorization_environment", ""),
        scope=ctx.get("authorization_scope", ""),
    )

    threat_mdl = ThreatModel(
        assets=ctx.get("protected_assets", []),
        threat_actors=ctx.get("threat_actors", []),
        attacker_goals=ctx.get("attacker_goals", []),
        attacker_capabilities=ctx.get("attacker_capabilities", []),
        entry_vectors=ctx.get("entry_vectors", []),
        trust_boundaries=ctx.get("trust_boundaries", []),
        existing_controls=ctx.get("existing_controls", []),
    )

    findings_rows = []
    for f in ctx.get("validated_findings", []):
        if isinstance(f, dict):
            findings_rows.append(FindingRow(**{
                k: f.get(k, "") for k in FindingRow.model_fields
            }))

    bf_rank = []
    for idx, r in enumerate(ranking_list[:MAX_FULLY_DEVELOPED_IDEAS]):
        bf_rank.append(BlackforgeRankingRow(
            position=idx + 1,
            proposal=r.get("title", r.get("proposal", "")),
            defensive_impact=r.get("defensive_impact", 0.0),
            bypass=r.get("bypass", 0.0),
            verifiability=r.get("verifiability", 0.0),
            feasibility=r.get("feasibility", 0.0),
            residual_risk=r.get("residual_risk", 0.0),
        ))

    decision = DecisionRecord(
        status="recommended" if top else "insufficient_evidence",
        reason="Primary proposal meets criteria" if top else "No proposals generated",
    )

    winner = BlackforgeWinner(
        name=top.get("title", ""),
        security_problem=ctx.get("central_problem", ctx.get("query", "")),
        technical_mechanism=top.get("mechanism", top.get("defensive_mechanism", "")),
        protected_assets=ctx.get("protected_assets", []),
        threat_actor=", ".join(ctx.get("threat_actors", [])),
        attack_surface=top.get("attack_surface", ""),
        security_property=top.get("security_property", ""),
        offensive_hypothesis=top.get("offensive_hypothesis", ""),
        defensive_response=top.get("defensive_response", top.get("mechanism", "")),
        validation_plan=top.get("validation_plan", top.get("verification_method", "")),
        expected_evidence=top.get("expected_evidence", []),
        likely_bypass=top.get("bypass_probable", top.get("bypass", "")),
        residual_risk=top.get("residual_risk", top.get("risk_level", "")),
        implementation_cost=str(top.get("implementation_cost", "")),
        why_it_wins=top.get("why_it_wins", top.get("description", "")),
    )

    return BlackforgeOutput(
        security_summary=sec_summary,
        authorization=authorization,
        threat_model=threat_mdl,
        findings=findings_rows,
        ranking=bf_rank,
        winner=winner,
        decision=decision,
    )


# ---------------------------------------------------------------------------
# Output validation
# ---------------------------------------------------------------------------

class OutputValidation(BaseModel):
    """Result of validating output against limits."""

    is_valid: bool
    idea_count: int = 0
    ranking_count: int = 0
    violations: list[str] = Field(default_factory=list)


def validate_output_limits(output: CribaOutput | BlackforgeOutput) -> OutputValidation:
    """Validate that output respects the limits from §5.5.

    - Max 1 primary recommendation (winning_proposal / winner)
    - Max 3 secondary alternatives (ranking)
    - Max 5 fully-developed ideas
    """
    violations: list[str] = []

    if isinstance(output, CribaOutput):
        idea_count = len(output.ideas)
        rank_count = len(output.ranking)
    elif isinstance(output, BlackforgeOutput):
        idea_count = len(output.findings)
        rank_count = len(output.ranking)
    else:
        return OutputValidation(is_valid=False, violations=["Unknown output type"])

    if idea_count > MAX_FULLY_DEVELOPED_IDEAS:
        violations.append(
            f"Ideas ({idea_count}) exceed maximum ({MAX_FULLY_DEVELOPED_IDEAS})"
        )
    if rank_count > MAX_SECONDARY_ALTERNATIVES:
        violations.append(
            f"Ranking entries ({rank_count}) exceed maximum ({MAX_SECONDARY_ALTERNATIVES})"
        )

    return OutputValidation(
        is_valid=len(violations) == 0,
        idea_count=idea_count,
        ranking_count=rank_count,
        violations=violations,
    )
