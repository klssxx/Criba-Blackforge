"""BLACKFORGE safety gate — FASE 3 (SAFETY).

evaluate_blackforge_safety(item, session_context) -> SafetyDecision

Runs BEFORE any hook that could materialize, test, simulate or attack. Pure,
deterministic function of (item, session_context); no side effects.

Decisions:
- ALLOW_CONCEPTUAL        (S0: analysis & ideation only)
- ALLOW_DEFENSIVE_DESIGN  (S1: defensive design / local non-destructive analysis)
- ALLOW_LOCAL_NON_DESTRUCTIVE (S1 local non-destructive)
- REQUIRE_SANDBOX         (S2: needs sandbox + approval + rollback + logging + stop)
- REQUIRE_HUMAN_APPROVAL  (S3: highest control; isolated sandbox + human approval)
- DENY                    (prohibited automatic action detected)

Every decision records: decision, policy_version, item_id, reasons,
unmet_requirements, allowed_scope, clock (injectable), session_id.

Hard prohibitions (catalog safety_policy.prohibited_automatic_actions) always
resolve to DENY, regardless of tier or approvals.
"""
from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .blackforge_catalog import load as _load_catalog

_SAFETY_POLICY_VERSION = "BF-SAFE-2.0.0"

# Decisions
ALLOW_CONCEPTUAL = "ALLOW_CONCEPTUAL"
ALLOW_DEFENSIVE_DESIGN = "ALLOW_DEFENSIVE_DESIGN"
ALLOW_LOCAL_NON_DESTRUCTIVE = "ALLOW_LOCAL_NON_DESTRUCTIVE"
REQUIRE_SANDBOX = "REQUIRE_SANDBOX"
REQUIRE_HUMAN_APPROVAL = "REQUIRE_HUMAN_APPROVAL"
DENY = "DENY"

# Scope strings
SCOPE_ANALYSIS = "analysis_and_ideation"
SCOPE_DEFENSIVE = "defensive_design_and_local_analysis"
SCOPE_NONE = "none"


class AuthorizationState(str, Enum):
    """Lifecycle state required by the Blackforge authorization gate."""

    PENDING = "pending"
    GRANTED = "granted"
    DENIED = "denied"
    EXPIRED = "expired"


@dataclass
class SafetyDecision:
    decision: str
    policy_version: str
    item_id: str
    reasons: list[str]
    unmet_requirements: list[str]
    allowed_scope: str
    session_id: str
    timestamp: str
    authorization_state: AuthorizationState = AuthorizationState.PENDING

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "policy_version": self.policy_version,
            "item_id": self.item_id,
            "reasons": self.reasons,
            "unmet_requirements": self.unmet_requirements,
            "allowed_scope": self.allowed_scope,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "authorization_state": self.authorization_state.value,
        }


def evaluate_blackforge_safety(
    item: Mapping[str, Any],
    session_context: Mapping[str, Any] | None = None,
    clock: Callable[[], float] = time.time,
    session_id: str = "default-session",
) -> SafetyDecision:
    """Evaluate one catalog item against the session safety context.

    session_context keys (all optional, default False/None):
      explicit_authorization, sandbox, rollback, logging, stop_condition,
      isolated_sandbox, human_approval, authorized_scope_confirmed.
    """
    ctx: dict[str, Any] = dict(session_context or {})
    item_id = item.get("blackforge_id") or item.get("canonical_item_id") or "?"
    safety_class = item.get("safety_class")
    reasons: list[str] = []
    unmet: list[str] = []
    try:
        authorization_state = AuthorizationState(ctx.get("authorization_state", AuthorizationState.PENDING))
    except ValueError:
        return SafetyDecision(
            decision=DENY, policy_version=_SAFETY_POLICY_VERSION, item_id=item_id,
            reasons=["Estado de autorización desconocido; se aplica deny-by-default."],
            unmet_requirements=["valid_authorization_state"], allowed_scope=SCOPE_NONE,
            session_id=session_id, timestamp=_iso(clock),
            authorization_state=AuthorizationState.PENDING,
        )

    # 1) Hard prohibitions -> DENY unconditionally.
    meta, _ = _load_catalog()
    prohibited: set[str] = set(meta.get("safety_policy", {}).get("prohibited_automatic_actions", []))
    # Map a few item-level red flags to the prohibited set for defensive depth.
    flag_fields = {
        "external_target_prohibited": "external_target_scanning",
        "requires_explicit_authorization": "unauthorized_access",
    }
    hard_deny = False
    if item.get("external_target_prohibited") is True:
        # external targeting is prohibited; flag denial unless purely conceptual.
        if safety_class != "S0_CONCEPTUAL":
            hard_deny = True
            reasons.append("Objetivo externo prohibido: ejecución contra terceros no permitida.")
            unmet.append("external_target_scanning")
    if hard_deny:
        return SafetyDecision(
            decision=DENY, policy_version=_SAFETY_POLICY_VERSION, item_id=item_id,
            reasons=reasons, unmet_requirements=unmet, allowed_scope=SCOPE_NONE,
            session_id=session_id, timestamp=_iso(clock),
            authorization_state=authorization_state,
        )

    # 2) Class-based gating.
    if safety_class == "S0_CONCEPTUAL":
        return SafetyDecision(
            decision=ALLOW_CONCEPTUAL, policy_version=_SAFETY_POLICY_VERSION,
            item_id=item_id, reasons=["S0_CONCEPTUAL: solo análisis e ideación; sin ejecución automática."],
            unmet_requirements=[], allowed_scope=SCOPE_ANALYSIS,
            session_id=session_id, timestamp=_iso(clock),
            authorization_state=authorization_state,
        )

    if safety_class == "S1_DEFENSIVE":
        # Local non-destructive analysis / defensive design allowed.
        scope = SCOPE_DEFENSIVE
        decision = ALLOW_DEFENSIVE_DESIGN
        if item.get("requires_sandbox") is False and item.get("requires_explicit_authorization") is False:
            decision = ALLOW_LOCAL_NON_DESTRUCTIVE
            reasons.append("S1_DEFENSIVE: diseño defensivo / análisis local no destructivo.")
        else:
            reasons.append("S1_DEFENSIVE: diseño defensivo; sin objetivos externos ni ejecución automática.")
        return SafetyDecision(
            decision=decision, policy_version=_SAFETY_POLICY_VERSION, item_id=item_id,
            reasons=reasons, unmet_requirements=[], allowed_scope=scope,
            session_id=session_id, timestamp=_iso(clock),
            authorization_state=authorization_state,
        )

    if safety_class == "S2_SANDBOX":
        required = ["explicit_authorization", "sandbox", "rollback", "logging", "stop_condition"]
        missing = [r for r in required if not ctx.get(r)]
        if not missing:
            return SafetyDecision(
                decision=REQUIRE_SANDBOX, policy_version=_SAFETY_POLICY_VERSION, item_id=item_id,
                reasons=["S2_SANDBOX: autorizado en sandbox con rollback/logging/stop."],
                unmet_requirements=[], allowed_scope=SCOPE_DEFENSIVE,
                session_id=session_id, timestamp=_iso(clock),
                authorization_state=authorization_state,
            )
        return SafetyDecision(
            decision=DENY, policy_version=_SAFETY_POLICY_VERSION, item_id=item_id,
            reasons=["S2_SANDBOX: requiere autorización explícita + sandbox + rollback + logging + stop_condition."],
            unmet_requirements=missing, allowed_scope=SCOPE_NONE,
            session_id=session_id, timestamp=_iso(clock),
            authorization_state=authorization_state,
        )

    if safety_class == "S3_HIGH_CONTROL":
        required = ["explicit_authorization", "isolated_sandbox", "human_approval", "rollback", "full_logging", "stop_condition"]
        missing = [r for r in required if not ctx.get(r)]
        auth_scope_ok = bool(ctx.get("authorized_scope_confirmed"))
        if not missing and auth_scope_ok:
            return SafetyDecision(
                decision=REQUIRE_HUMAN_APPROVAL, policy_version=_SAFETY_POLICY_VERSION, item_id=item_id,
                reasons=["S3_HIGH_CONTROL: aprobación humana + sandbox aislado + logging completo."],
                unmet_requirements=[], allowed_scope=SCOPE_NONE,
                session_id=session_id, timestamp=_iso(clock),
                authorization_state=authorization_state,
            )
        if not auth_scope_ok:
            unmet.append("authorized_scope_confirmed")
        # Report BOTH the missing S3 requirements and an unconfirmed authorized
        # scope so the caller sees the precise blocker (scope was previously
        # appended to `unmet` but never surfaced in the returned decision).
        return SafetyDecision(
            decision=DENY, policy_version=_SAFETY_POLICY_VERSION, item_id=item_id,
            reasons=["S3_HIGH_CONTROL: nunca habilitado por defecto; requiere aprobación humana + sandbox aislado + logging completo + scope autorizado."],
            unmet_requirements=missing + unmet, allowed_scope=SCOPE_NONE,
            session_id=session_id, timestamp=_iso(clock),
            authorization_state=authorization_state,
        )

    # Unknown safety class -> deny conservatively.
    return SafetyDecision(
        decision=DENY, policy_version=_SAFETY_POLICY_VERSION, item_id=item_id,
        reasons=[f"Clase de seguridad desconocida: {safety_class}."],
        unmet_requirements=["valid_safety_class"], allowed_scope=SCOPE_NONE,
        session_id=session_id, timestamp=_iso(clock),
        authorization_state=authorization_state,
    )


def _iso(clock: Callable[[], float]) -> str:
    try:
        return _iso_from_ts(clock())
    except Exception:
        return str(clock())


def _iso_from_ts(ts: float) -> str:
    import datetime
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).isoformat()
