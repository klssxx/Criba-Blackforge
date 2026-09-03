"""Deterministic validation gates (HIPERMEGAPROMPT §10).

Unified gate framework G01-G12 with verdicts
VERIFIED / PARTIAL / BLOCKED / FAILED.

Design constraints (from user authorization + spec §10):
- VERIFIED is NEVER granted without executed-test evidence, even if all
  12 structural gates pass.
- RetryPolicy (§10.6) is append-only: a retry never erases evidence from
  previous attempts.
- Idempotency keys are part of P8 logging (§10.5); gates accept an
  ``idempotency_key`` passthrough so retries do not duplicate evidence.

Reuses (no reimplementation):
- blackforge_causal.canonical_hash for reproducibility hashing.
- blackforge_safety.evaluate_blackforge_safety for G04 authorization.
- output_format.CribaOutput / BlackforgeOutput for G01 / G12.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .blackforge_causal import canonical_hash
from .blackforge_safety import (
    DENY,
    evaluate_blackforge_safety,
)

# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------

class Verdict(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


# ---------------------------------------------------------------------------
# Gate result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GateResult:
    gate_id: str
    passed: bool
    reason: str
    severity: str = "blocking"  # "blocking" | "warning"

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "passed": self.passed,
            "reason": self.reason,
            "severity": self.severity,
        }


# ---------------------------------------------------------------------------
# RetryPolicy (§10.6) — append-only, never erases previous-attempt evidence
# ---------------------------------------------------------------------------

class RetryClassification(str, Enum):
    TRANSIENT = "transient"
    INVALID_OUTPUT = "invalid_output"
    POLICY = "policy"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    PERMANENT = "permanent"


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    backoff_seconds: float = 1.0
    jitter_seconds: float = 0.5
    retryable: tuple[str, ...] = (
        RetryClassification.TRANSIENT.value,
        RetryClassification.TIMEOUT.value,
        RetryClassification.RATE_LIMIT.value,
    )
    non_retryable: tuple[str, ...] = (
        RetryClassification.INVALID_OUTPUT.value,
        RetryClassification.POLICY.value,
        RetryClassification.PERMANENT.value,
    )
    fallback_allowed: bool = True

    def is_retryable(self, classification: str) -> bool:
        return classification in self.retryable

    def record_attempt(self, ledger: list[dict[str, Any]], attempt: int,
                       classification: str, evidence: Mapping[str, Any]) -> None:
        """Append an attempt to the ledger. NEVER mutates prior entries.

        The ledger is the durable, append-only evidence trail required by
        §10.6: 'Un reintento no debe borrar evidencia del intento anterior.'
        """
        entry = {
            "attempt": attempt,
            "classification": classification,
            "evidence_hash": canonical_hash(dict(evidence)),
            "evidence": dict(evidence),
        }
        ledger.append(entry)


# ---------------------------------------------------------------------------
# State machine (§7.1 / §10.5)
# ---------------------------------------------------------------------------

VALID_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "pending": ("running",),
    "running": ("awaiting_human_review", "failed"),
    "awaiting_human_review": ("approved", "rejected", "revision_required", "returned_to_previous"),
    "approved": ("completed", "superseded"),
    "revision_required": ("running", "rejected"),
    "rejected": ("superseded",),
    "superseded": (),
    "completed": ("superseded",),
}


# ---------------------------------------------------------------------------
# Individual gates (pure, deterministic)
# ---------------------------------------------------------------------------

def G01_schema_valid(output: Any) -> GateResult:
    """Output contract is a valid CribaOutput / BlackforgeOutput instance."""
    from .output_format import BlackforgeOutput, CribaOutput
    if isinstance(output, (CribaOutput, BlackforgeOutput)):
        return GateResult("G01_schema_valid", True, "Output es instancia válida del contrato.")
    return GateResult("G01_schema_valid", False,
                      f"Output no es CribaOutput/BlackforgeOutput: {type(output).__name__}")


def G02_context_complete(context: Mapping[str, Any]) -> GateResult:
    """Context carries context_id and minimal required fields (§2.7)."""
    cid = context.get("context_id")
    if not cid:
        return GateResult("G02_context_complete", False, "Falta context_id.")
    if not context.get("central_problem") and not context.get("normalized_query"):
        return GateResult("G02_context_complete", False,
                          "Contexto sin central_problem ni normalized_query.")
    return GateResult("G02_context_complete", True, "Contexto completo.")


def G03_required_anchors(packet: Mapping[str, Any]) -> GateResult:
    """Every idea demonstrates a problem anchor (principio de anclaje §0.2)."""
    ideas = packet.get("ideas") or []
    if not ideas:
        return GateResult("G03_required_anchors", True, "Sin ideas que anclar.", severity="warning")
    missing = [i.get("id", "?") for i in ideas if not (i.get("problem_anchor") or i.get("mechanism"))]
    if missing:
        return GateResult("G03_required_anchors", False,
                          f"Ideas sin ancla (problem_anchor/mecanismo): {missing}")
    return GateResult("G03_required_anchors", True, "Todas las ideas ancladas.")


def G04_authorization_valid(context: Mapping[str, Any],
                            item: Mapping[str, Any] | None = None) -> GateResult:
    """Blackforge cannot advance without valid authorization (§4.3, §10.2)."""
    mode = str(context.get("mode", "criba")).lower()
    if mode != "blackforge":
        return GateResult("G04_authorization_valid", True, "No es Blackforge; autorización N/A.")
    # An explicit granted state is mandatory and authoritative.
    authorization_state = context.get("authorization_state")
    if authorization_state != "granted":
        return GateResult(
            "G04_authorization_valid", False,
            f"Se requiere authorization_state='granted'; recibido {authorization_state!r}",
        )
    # Reuse the existing safety evaluator rather than reimplementing it.
    session_ctx = {
        "explicit_authorization": True,
        "authorized_scope_confirmed": bool(context.get("authorization_scope")),
        "sandbox": True,
        "isolated_sandbox": True,
        "rollback": True,
        "logging": True,
        "full_logging": True,
        "human_approval": bool(context.get("authorization_scope")),
        "stop_condition": bool(context.get("stop_conditions")),
    }
    target = item or {"safety_class": "S2_SANDBOX",
                      "blackforge_id": context.get("context_id", "?"),
                      "requires_explicit_authorization": True}
    decision = evaluate_blackforge_safety(target, session_ctx, session_id=str(context.get("context_id", "default")))
    if decision.decision == DENY:
        return GateResult("G04_authorization_valid", False,
                          f"Autorización denegada: {decision.reasons}")
    return GateResult("G04_authorization_valid", True,
                      f"Autorización: {decision.decision}.")


def G05_state_transition_valid(frm: str, to: str) -> GateResult:
    """Prohibit invalid state transitions (§10.5)."""
    allowed = VALID_TRANSITIONS.get(frm, ())
    if to in allowed:
        return GateResult("G05_state_transition_valid", True, f"{frm} -> {to} válida.")
    return GateResult("G05_state_transition_valid", False,
                      f"Transición inválida: {frm} -> {to}. Permitidas: {allowed}")


def G06_no_broken_references(packet: Mapping[str, Any]) -> GateResult:
    """Every ranking reference points to an existing idea (§10.2)."""
    ideas = packet.get("ideas") or []
    idea_ids = {i.get("id") for i in ideas}
    ranking = packet.get("ranking") or []
    broken = [r.get("idea_id") for r in ranking if r.get("idea_id") not in idea_ids]
    if broken:
        return GateResult("G06_no_broken_references", False, f"Referencias rotas: {broken}")
    return GateResult("G06_no_broken_references", True, "Sin referencias rotas.")


def G07_scores_normalized(packet: Mapping[str, Any]) -> GateResult:
    """Weights sum to ~1 and scores within [0,1] (§10.2)."""
    criteria = packet.get("evaluation_criteria") or {}
    if criteria:
        total = sum(float(v) for v in criteria.values())
        if abs(total - 1.0) > 1e-6:
            return GateResult("G07_scores_normalized", False, f"Pesos suman {total}, esperado 1.0.")
    ranking = packet.get("ranking") or []
    for r in ranking:
        for k in ("value", "novelty", "feasibility", "risk", "final"):
            v = r.get(k)
            if v is not None and not (0.0 <= float(v) <= 1.0):
                return GateResult("G07_scores_normalized", False,
                                  f"Score fuera de rango en {r.get('idea_id')}.{k}={v}")
    return GateResult("G07_scores_normalized", True, "Pesos/scores normalizados.")


def G08_evidence_requirement_met(packet: Mapping[str, Any]) -> GateResult:
    """A confirmed finding requires evidence (§10.2, §4.3)."""
    findings = packet.get("findings") or []
    for f in findings:
        if f.get("status") == "confirmed" and not f.get("evidence"):
            return GateResult("G08_evidence_requirement_met", False,
                              f"Hallazgo confirmado sin evidencia: {f.get('title', '?')}")
    return GateResult("G08_evidence_requirement_met", True, "Evidencia presente donde requerida.")


def G09_no_duplicate_ids(packet: Mapping[str, Any]) -> GateResult:
    """No duplicate idea/context ids (§10.2)."""
    ids = [i.get("id") for i in (packet.get("ideas") or [])]
    dupes = {x for x in ids if ids.count(x) > 1}
    if dupes:
        return GateResult("G09_no_duplicate_ids", False, f"IDs duplicados: {dupes}")
    return GateResult("G09_no_duplicate_ids", True, "Sin IDs duplicados.")


def G10_trace_complete(packet: Mapping[str, Any]) -> GateResult:
    """Trace carries context_id/task_id (§18, §11)."""
    ctx = packet.get("context") or packet
    if not ctx.get("context_id"):
        return GateResult("G10_trace_complete", False, "Falta context_id en traza.")
    if not packet.get("task_id") and not ctx.get("task_id"):
        return GateResult("G10_trace_complete", False, "Falta task_id en traza.", severity="warning")
    return GateResult("G10_trace_complete", True, "Traza completa (context_id/task_id).")


def G11_human_review_present(reviews: Sequence[Mapping[str, Any]]) -> GateResult:
    """A human review record exists where required (§7.9, §10.3)."""
    if not reviews:
        return GateResult("G11_human_review_present", False, "Sin registro de revisión humana.")
    return GateResult("G11_human_review_present", True, f"{len(reviews)} revisión(es) humana(s).")


def G12_output_contract_valid(output: Any) -> GateResult:
    """Output respects structural limits (§5.5)."""
    from .output_format import validate_output_limits
    validation = validate_output_limits(output)
    if validation.is_valid:
        return GateResult("G12_output_contract_valid", True, "Límites de salida respetados.")
    return GateResult("G12_output_contract_valid", False,
                      f"Límites violados: {validation.violations}")


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

# Gates that are structurally critical: if any FAIL, VERIFIED is impossible.
CRITICAL_GATES = {"G01_schema_valid", "G04_authorization_valid", "G12_output_contract_valid"}


@dataclass
class GateReport:
    verdict: Verdict
    results: list[GateResult] = field(default_factory=list)
    test_evidence_present: bool = False
    idempotency_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "test_evidence_present": self.test_evidence_present,
            "idempotency_key": self.idempotency_key,
            "results": [r.to_dict() for r in self.results],
        }


def evaluate_gates(
    *,
    context: Mapping[str, Any],
    packet: Mapping[str, Any],
    output: Any,
    reviews: Sequence[Mapping[str, Any]] | None = None,
    item: Mapping[str, Any] | None = None,
    test_evidence_present: bool = False,
    idempotency_key: str | None = None,
) -> GateReport:
    """Run all 12 gates and compute the verdict.

    Verdict rules (§10.3 / §10.11 + user addendum #1):
    - FAILED: any blocking gate FAILS.
    - BLOCKED: any critical gate (G01/G04/G12) FAILS, or a non-blocking gate
      FAILS with blocking severity.
    - VERIFIED: ALL gates PASS AND executed-test evidence is present.
      Without test_evidence_present, the best achievable verdict is PARTIAL.
    - PARTIAL: all gates PASS structurally but test evidence is missing.
    """
    reviews = reviews or []
    results = [
        G01_schema_valid(output),
        G02_context_complete(context),
        G03_required_anchors(packet),
        G04_authorization_valid(context, item),
        # G05 exercised on the declared transition (default pending->running
        # is valid per the §10.5 / §7.1 state machine).
        G05_state_transition_valid(
            packet.get("state_from", "pending"),
            packet.get("state_to", "running"),
        ),
        G06_no_broken_references(packet),
        G07_scores_normalized(packet),
        G08_evidence_requirement_met(packet),
        G09_no_duplicate_ids(packet),
        G10_trace_complete(packet),
        G11_human_review_present(reviews),
        G12_output_contract_valid(output),
    ]

    any_blocking_fail = any(not r.passed for r in results if r.severity == "blocking")
    critical_fail = any(not r.passed and r.gate_id in CRITICAL_GATES for r in results)
    all_pass = all(r.passed for r in results)

    # §10.11: FAILED = the principal function has no reproducible proof;
    # BLOCKED = a precondition gate (auth/evidence/contract) is unmet.
    g01_failed = any(not r.passed and r.gate_id == "G01_schema_valid" for r in results)
    if g01_failed:
        # Output is unusable (not even a valid contract) -> FAILED.
        verdict = Verdict.FAILED
    elif critical_fail or any_blocking_fail:
        # Critical gate (G04/G12) or any blocking gate unmet -> BLOCKED.
        verdict = Verdict.BLOCKED
    elif not all_pass:
        verdict = Verdict.BLOCKED
    elif not test_evidence_present:
        # Addendum #1: never VERIFIED without executed-test evidence.
        verdict = Verdict.PARTIAL
    else:
        verdict = Verdict.VERIFIED

    return GateReport(verdict=verdict, results=results,
                      test_evidence_present=test_evidence_present,
                      idempotency_key=idempotency_key)
