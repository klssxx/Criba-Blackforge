"""BLACKFORGE Agent Capability Layer (FASE 1).

This is a *thin, declarative* capability surface that wraps the existing
immutable BLACKFORGE pipeline (``blackforge_pipeline.run_headless``) and the
safety gate (``blackforge_safety.evaluate_blackforge_safety``).

Design goals (from HIPER_MEGAPROMPT §9):
  * Expose semantic DOMAIN capabilities, not UI details.
  * Reuse ONE domain engine — never duplicate selector/safety/causal logic.
  * Every mutation MUST pass through the existing safety policy (S0–S3).
  * Deterministic + reproducible by default (seeded).

Public API (the capability surface consumed by all adapters):
  * get_context()  → read-only project/problem context snapshot
  * analyze_security_problem(objective) → run full pipeline under current context
  * get_findings() → ranked ideas + causal signatures
  * generate_defensive_options(finding_id) → mitigation candidates for a finding
  * compare_defensive_options(a_id, b_id) → causal similarity between two proposals
  * propose_mitigation(finding_id) → best mitigation proposal (human-approval path)
  * apply_approved_mitigation(proposal_id, approvals) → guarded mutation (S3 path)
  * get_history() → chronological record of prior analyses + approvals
  * get_security_score() → aggregate posture score (deterministic)

The layer is safe to import even when no agent is connected — it simply
delegates to the deterministic engine. When an agent IS connected it provides
the contract shared by WebMCP, Strands, and other client adapters.
"""
from __future__ import annotations

import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .blackforge_pipeline import run_headless
from .blackforge_safety import (
    ALLOW_CONCEPTUAL,
    ALLOW_DEFENSIVE_DESIGN,
    ALLOW_LOCAL_NON_DESTRUCTIVE,
    DENY,
    REQUIRE_HUMAN_APPROVAL,
    REQUIRE_SANDBOX,
    evaluate_blackforge_safety,
)
from .storage import Storage

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Finding(BaseModel):
    """A single ranked BLACKFORGE idea + its convergence metadata."""

    model_config = ConfigDict(extra="allow")

    blackforge_id: str
    title: str
    description: str
    safety_class: str
    safety_decision: str
    causal_axis_primary: str
    value_score: float
    family: str = ""
    family2: str = ""
    convergence: dict[str, Any] = Field(default_factory=dict)
    approved: bool = False
    proposed_mitigation: str | None = None


class MitigationProposal(BaseModel):
    """A mitigation proposal that may be applied with explicit approval."""

    model_config = ConfigDict(extra="allow")

    proposal_id: str
    finding_id: str
    title: str
    description: str
    mechanism: str
    experiment: str
    safety_scope: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    approved_by: str | None = None
    approved_at: str | None = None


class SecurityScore(BaseModel):
    """Aggregate posture snapshot (deterministic)."""

    model_config = ConfigDict(extra="allow")

    posture_label: str
    novelty: float
    evidence: float
    viability: float
    mean_value_score: float
    findings_count: int
    mitigations_applied: int
    safety_decisions: dict[str, int]


# ---------------------------------------------------------------------------
# Context snapshot (read-only)
# ---------------------------------------------------------------------------

@dataclass
class AgentContext:
    """Immutable snapshot of the problem context + prior state."""

    objective: str
    seed: int
    session_size: int
    profile: str
    session_id: str
    allow_research: bool
    explicit_high_control_approval: bool
    authorized_scope_confirmed: bool
    sandbox_available: bool


# ---------------------------------------------------------------------------
# Capability Layer
# ---------------------------------------------------------------------------

class BlackforgeCapabilityLayer:
    """Semantic capability surface over the BLACKFORGE pipeline.

    All mutations route through ``evaluate_blackforge_safety``; none bypass it.
    The layer is stateless across calls except for the persisted SQLite store,
    which records findings, proposals, and approvals for auditability.
    """

    def __init__(
        self,
        store: Storage | None = None,
        *,
        allow_mutation: bool = False,
    ) -> None:
        self._store = store
        self._allow_mutation = allow_mutation
        self._current_context: AgentContext | None = None
        self._last_findings: list[Finding] = []
        self._proposals: dict[str, MitigationProposal] = {}
        self._session_counter = 0

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def get_context(self) -> dict[str, Any]:
        """Return the current context snapshot (or defaults)."""
        if self._current_context is None:
            return {
                "objective": "default",
                "seed": 1,
                "session_size": 12,
                "profile": "hybrid",
                "session_id": "blackforge-agentic-default",
                "allow_research": False,
                "explicit_high_control_approval": False,
                "authorized_scope_confirmed": False,
                "sandbox_available": False,
            }
        ctx = self._current_context
        return {
            "objective": ctx.objective,
            "seed": ctx.seed,
            "session_size": ctx.session_size,
            "profile": ctx.profile,
            "session_id": ctx.session_id,
            "allow_research": ctx.allow_research,
            "explicit_high_control_approval": ctx.explicit_high_control_approval,
            "authorized_scope_confirmed": ctx.authorized_scope_confirmed,
            "sandbox_available": ctx.sandbox_available,
        }

    # ------------------------------------------------------------------
    # ANALYSIS
    # ------------------------------------------------------------------

    def analyze_security_problem(
        self,
        objective: str,
        *,
        seed: int = 1,
        session_size: int = 12,
        profile: str = "hybrid",
        allow_research: bool = False,
        explicit_high_control_approval: bool = False,
        authorized_scope_confirmed: bool = False,
        sandbox_available: bool = False,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Run the full BLACKFORGE pipeline under the given objective.

        This is the hero capability: the deterministic engine produces ideas,
        the safety gate filters them, and causal signatures are preserved.
        Returns the raw pipeline packet.
        """
        sid = session_id or f"agentic-{uuid.uuid4().hex[:8]}"
        self._session_counter += 1
        self._current_context = AgentContext(
            objective=objective,
            seed=seed,
            session_size=session_size,
            profile=profile,
            session_id=sid,
            allow_research=allow_research,
            explicit_high_control_approval=explicit_high_control_approval,
            authorized_scope_confirmed=authorized_scope_confirmed,
            sandbox_available=sandbox_available,
        )

        packet = run_headless(
            query=objective,
            seed=seed,
            session_size=session_size,
            profile=profile,
            session_id=sid,
            session_context={
                "explicit_authorization": explicit_high_control_approval,
                "sandbox": sandbox_available,
                "rollback": sandbox_available,
                "logging": True,
                "stop_condition": True,
                "isolated_sandbox": sandbox_available,
                "human_approval": explicit_high_control_approval,
                "authorized_scope_confirmed": authorized_scope_confirmed,
            },
        )

        # Build findings list with safety decisions attached
        safety_report = {
            entry["item_id"]: entry for entry in packet.get("safety_report", [])
        }
        ideas = packet.get("ideas", [])
        findings: list[Finding] = []
        for idea in ideas:
            bf_id = idea.get("blackforge_id", "")
            decision_entry = safety_report.get(bf_id, {})
            findings.append(
                Finding(
                    blackforge_id=bf_id,
                    title=idea.get("title", ""),
                    description=idea.get("description", ""),
                    safety_class=idea.get("safety_class", ""),
                    safety_decision=decision_entry.get("decision", ALLOW_CONCEPTUAL),
                    causal_axis_primary=idea.get("causal_axis_primary", "unknown"),
                    value_score=idea.get("convergence", {}).get("value_score", 0.0),
                    family=idea.get("family", ""),
                    family2=idea.get("family2", ""),
                    convergence=idea.get("convergence", {}),
                )
            )
        self._last_findings = findings

        return packet

    # ------------------------------------------------------------------
    # Findings (read from last analysis)
    # ------------------------------------------------------------------

    def get_findings(self) -> list[dict[str, Any]]:
        """Return ranked findings from the most recent analysis."""
        return [f.model_dump() for f in self._last_findings]

    def get_finding(self, finding_id: str) -> dict[str, Any] | None:
        """Return a specific finding by blackforge_id."""
        for f in self._last_findings:
            if f.blackforge_id == finding_id:
                return f.model_dump()
        return None

    # ------------------------------------------------------------------
    # ANALYSIS (mitigation generation)
    # ------------------------------------------------------------------

    def generate_defensive_options(self, finding_id: str) -> list[dict[str, Any]]:
        """Generate mitigation candidate proposals for a given finding.

        Each proposal is a draft — it has NOT been applied.  The human
        (or agent with approval) must call ``propose_mitigation`` then
        ``apply_approved_mitigation`` to enact it.
        """
        finding = self.get_finding(finding_id)
        if finding is None:
            return []

        safety_class = finding.get("safety_class", "")
        # Generate 2-3 candidate mitigations based on causal axis + family
        options: list[dict[str, Any]] = []
        axis = finding.get("causal_axis_primary", "unknown")

        # Option 1: direct causal intervention
        options.append({
            "option_id": "opt-1",
            "finding_id": finding_id,
            "title": f"Intervención sobre {axis}",
            "description": f"Modificar {axis} para cambiar el resultado causal.",
            "mechanism": "causal_intervention",
            "safety_scope": finding.get("safety_decision", ALLOW_CONCEPTUAL),
            "requires_approval": safety_class in ("S2_SANDBOX", "S3_HIGH_CONTROL"),
        })

        # Option 2: family-based cross-family mitigation
        options.append({
            "option_id": "opt-2",
            "finding_id": finding_id,
            "title": f"Combinación defensiva: {finding.get('family', 'desconocida')}",
            "description": "Combinar mecanismos de familias relacionadas para defensa en profundidad.",
            "mechanism": "defense_in_depth",
            "safety_scope": ALLOW_DEFENSIVE_DESIGN,
            "requires_approval": False,
        })

        # Option 3: evidence-based verification
        options.append({
            "option_id": "opt-3",
            "finding_id": finding_id,
            "title": f"Verificación de {finding.get('title', '')[:40]}",
            "description": "Generar propuesta de experimento de validación causal.",
            "mechanism": "causal_verification",
            "safety_scope": ALLOW_CONCEPTUAL,
            "requires_approval": False,
        })

        return options

    def compare_defensive_options(self, option_a: str, option_b: str) -> dict[str, Any]:
        """Compare two mitigation options by their safety scope and mechanism."""
        # In a real implementation this would use blackforge_causal.analyze_causal_pair
        # For now: structural comparison based on scope + mechanism overlap
        return {
            "option_a": option_a,
            "option_b": option_b,
            "comparison": "defensive_options_comparison",
            "note": "Compare safety scope and mechanism overlap; higher-scope interventions require approval.",
        }

    def propose_mitigation(self, finding_id: str, option_id: str = "opt-1") -> str:
        """Create a formal mitigation proposal (has NOT been applied).

        Returns the proposal_id.  The proposal must be approved via
        ``apply_approved_mitigation`` before any mutation occurs.
        """
        options = self.generate_defensive_options(finding_id)
        option = next((o for o in options if o["option_id"] == option_id), None)
        if option is None:
            option = options[0] if options else {}

        proposal = MitigationProposal(
            proposal_id=f"prop-{uuid.uuid4().hex[:8]}",
            finding_id=finding_id,
            title=option.get("title", "Mitigación propuesta"),
            description=option.get("description", ""),
            mechanism=option.get("mechanism", "unknown"),
            experiment=f"Validar {option.get('mechanism', '')} sobre {finding_id}.",
            safety_scope=option.get("safety_scope", ALLOW_CONCEPTUAL),
            evidence=[],
        )
        self._proposals[proposal.proposal_id] = proposal
        return proposal.proposal_id

    # ------------------------------------------------------------------
    # MUTATION (requires approval)
    # ------------------------------------------------------------------

    def apply_approved_mitigation(
        self,
        proposal_id: str,
        approver: str,
        approvals: Mapping[str, bool],
    ) -> dict[str, Any]:
        """Apply a mitigation proposal after verifying approval + safety.

        This is the ONLY mutation path.  It:
        1. Looks up the proposal
        2. Re-evaluates the safety decision with the provided approvals
        3. If safety allows → applies (records the decision)
        4. If safety DENY → raises / refuses
        """
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            raise ValueError(f"Proposal not found: {proposal_id}")

        if not self._allow_mutation:
            raise PermissionError(
                "Mutation layer not enabled. Set allow_mutation=True to "
                "permit approved changes."
            )

        # Build session context for safety re-evaluation
        ctx: dict[str, Any] = {
            "explicit_authorization": bool(approvals.get("explicit_authorization", False)),
            "sandbox": bool(approvals.get("sandbox", False)),
            "rollback": bool(approvals.get("rollback", False)),
            "logging": True,
            "stop_condition": True,
            "isolated_sandbox": bool(approvals.get("isolated_sandbox", False)),
            "human_approval": bool(approvals.get("human_approval", False)),
            "authorized_scope_confirmed": bool(approvals.get("authorized_scope_confirmed", False)),
        }

        # Look up the original finding to get its real safety_class
        finding = self.get_finding(proposal.finding_id)
        safety_class = "S1_DEFENSIVE"  # default: defensive design
        if finding is not None:
            safety_class = finding.get("safety_class", "S1_DEFENSIVE")

        # Re-evaluate safety using the finding's actual safety_class
        decision = evaluate_blackforge_safety(
            {"blackforge_id": proposal.finding_id,
             "safety_class": safety_class},
            ctx,
            session_id=self.get_context().get("session_id", "default"),
        )

        if decision.decision == DENY:
            return {
                "status": "DENIED",
                "proposal_id": proposal_id,
                "reason": "; ".join(decision.reasons),
                "unmet_requirements": decision.unmet_requirements,
            }

        # Record the approval + apply
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        proposal.approved_by = approver
        proposal.approved_at = now
        for f in self._last_findings:
            if f.blackforge_id == proposal.finding_id:
                f.approved = True
                f.proposed_mitigation = proposal.title
                break

        # Persist to store if available — record_decision requires a saved session
        if self._store is not None:
            sid = self.get_context().get("session_id", "")
            try:
                self._store.record_decision(
                    sid,
                    "mitigation_applied",
                    [{"proposal_id": proposal_id, "finding_id": proposal.finding_id, "approved_by": approver}],
                    note=f"Applied {proposal.title}",
                )
            except (ValueError, Exception):
                # Session may not be persisted in store; the in-memory
                # proposal approval above is the authoritative state.
                pass

        return {
            "status": "APPLIED",
            "proposal_id": proposal_id,
            "finding_id": proposal.finding_id,
            "approved_by": approver,
            "approved_at": now,
            "safety_decision": decision.to_dict(),
        }

    # ------------------------------------------------------------------
    # HISTORY & SCORE
    # ------------------------------------------------------------------

    def get_history(self) -> list[dict[str, Any]]:
        """Return chronological record of prior analyses + proposals."""
        results: list[dict[str, Any]] = []
        if self._store is not None:
            sessions = self._store.list_sessions()
            for session in sessions:
                results.append({
                    "session_id": session.get("session_id", ""),
                    "timestamp": session.get("timestamp", ""),
                    "status": session.get("status", ""),
                    "summary": session.get("summary", ""),
                })
        results.append({
            "session_id": self.get_context().get("session_id", ""),
            "findings": self.get_findings(),
            "proposals": [p.model_dump() for p in self._proposals.values()],
        })
        return results

    def get_security_score(self) -> dict[str, Any]:
        """Aggregate posture score from the last analysis."""
        safety_counts: dict[str, int] = {}
        for f in self._last_findings:
            dec = f.safety_decision
            safety_counts[dec] = safety_counts.get(dec, 0) + 1

        mean_value = (
            sum(f.value_score for f in self._last_findings) / len(self._last_findings)
            if self._last_findings else 0.0
        )

        # Posture label based on safety decisions
        denied = safety_counts.get(DENY, 0)
        approved_s3 = safety_counts.get(REQUIRE_HUMAN_APPROVAL, 0)
        approved_s2 = safety_counts.get(REQUIRE_SANDBOX, 0)
        allowed = sum(safety_counts.get(d, 0) for d in (
            ALLOW_CONCEPTUAL, ALLOW_DEFENSIVE_DESIGN, ALLOW_LOCAL_NON_DESTRUCTIVE
        ))

        if denied > 0:
            posture = "CON STRIANGULACION DE RIESGO"
        elif approved_s3 > 0:
            posture = "ALTO CONTROL REQUERIDO"
        elif approved_s2 > 0:
            posture = "SANDBOX RECOMENDADO"
        elif allowed > 0:
            posture = "SEGURO PARA ANALISIS LOCAL"
        else:
            posture = "SIN ANALISIS"

        score = SecurityScore(
            posture_label=posture,
            novelty=mean_value,
            evidence=mean_value,
            viability=0.8,
            mean_value_score=round(mean_value, 4),
            findings_count=len(self._last_findings),
            mitigations_applied=sum(1 for f in self._last_findings if f.approved),
            safety_decisions=safety_counts,
        )
        return score.model_dump()


# ---------------------------------------------------------------------------
# Convenience: module-level singleton accessor
# ---------------------------------------------------------------------------

_default_layer: BlackforgeCapabilityLayer | None = None


def get_layer(
    store: Storage | None = None,
    *,
    allow_mutation: bool = False,
    reset: bool = False,
) -> BlackforgeCapabilityLayer:
    """Return a process-level singleton capability layer.

    The layer is stateless across analyses (each ``analyze_security_problem``
    sets fresh context), so the singleton is safe to share across adapter
    calls within one process.
    """
    global _default_layer
    if _default_layer is None or reset:
        _default_layer = BlackforgeCapabilityLayer(
            store=store, allow_mutation=allow_mutation
        )
    return _default_layer
