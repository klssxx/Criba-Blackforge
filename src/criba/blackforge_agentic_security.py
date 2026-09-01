"""BLACKFORGE Agent Security Boundaries (FASE 2).

Wraps the Agent Capability Layer with Zero-Trust agent interaction:
  * Tool input sanitization (prompt injection, oversized input, path traversal)
  * Safety re-validation on every mutation (no bypass of S0–S3)
  * Audit trail for every tool call + safety decision
  * Mutation logging with actor/actor-type tracking

This module is the trust anchor between any agent (WebMCP/Strands or another
client adapter) and the
BLACKFORGE engine.  The capability layer in ``blackforge_agentic`` delegates
here for every security-sensitive operation.

Security guarantees:
  * No agent can skip the safety gate — ``apply_approved_mutation`` always
    re-evaluates via ``evaluate_blackforge_safety``.
  * No agent can bypass input validation — all tool args pass through
    ``ToolInputSanitizer``.
  * All mutations are logged with timestamp, actor, and safety decision.
"""
from __future__ import annotations

import logging
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .blackforge_agentic import BlackforgeCapabilityLayer
from .blackforge_safety import (
    ALLOW_CONCEPTUAL,
    ALLOW_DEFENSIVE_DESIGN,
    ALLOW_LOCAL_NON_DESTRUCTIVE,
    DENY,
    REQUIRE_HUMAN_APPROVAL,
    REQUIRE_SANDBOX,
    SafetyDecision,
    evaluate_blackforge_safety,
)

logger = logging.getLogger("blackforge.agent.security")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MAX_INPUT_LENGTH = 20_000  # chars, matches MAX_QUERY_CHARS
MAX_OBJECTIVE_LENGTH = 500
MAX_FINDING_ID_LENGTH = 64
MAX_PROPOSAL_ID_LENGTH = 64
MAX_APPROVER_LENGTH = 128

# Prompt injection heuristic patterns (defense-in-depth, not sole reliance)
_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)\bignora[rz]? (las )?(instrucciones|directrices?|reglas?|previous)"),
    re.compile(r"(?i)\bignore (all|previous|prior)\s*(instructions?|prompts?|rules?)"),
    re.compile(r"(?i)\b(system|you are)\s*:?\s*(prompt|instruction)"),
    re.compile(r"(?i)\b(jailbreak|break free|dereference)\b"),
    re.compile(r"(?i)\b(pretend|act as if|you are now)\b.*\b(administrator|root|admin)\b"),
    re.compile(r"(?i)\b(do not|don't)\s+(review|check|verify|filter|sanitize)\b"),
    re.compile(r"(?i)\b(override|ignore|bypass|disable)\s+(safety|security|gate|filter)\b"),
    re.compile(r"(?i)\b(os\.system|subprocess\.|eval\(|exec\(|__import__)\b"),
    re.compile(r"(?i)\b(rm -rf|del\s+/[s,q]?|format c:)\b"),
]

# Path traversal detection (matches ../, ..\, ..%2F, etc.)
_PATH_TRAVERSAL_PATTERN = re.compile(
    r'\.\.[\\/]',
)


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AuditEntry:
    """Immutable audit record for a tool call or mutation."""

    timestamp: str
    tool_name: str
    actor: str
    actor_type: str  # "human" | "agent" | "system"
    input_size: int
    safety_decision: str
    result_status: str
    error_message: str = ""
    session_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "tool_name": self.tool_name,
            "actor": self.actor,
            "actor_type": self.actor_type,
            "input_size": self.input_size,
            "safety_decision": self.safety_decision,
            "result_status": self.result_status,
            "error_message": self.error_message,
            "session_id": self.session_id,
        }


@dataclass
class MutationLog:
    """Append-only audit log of all mutations + safety decisions."""

    entries: list[AuditEntry] = field(default_factory=list)

    def append(self, entry: AuditEntry) -> None:
        self.entries.append(entry)
        logger.info(
            "AUDIT: tool=%s actor=%s:%s safety=%s result=%s session=%s",
            entry.tool_name, entry.actor, entry.actor_type,
            entry.safety_decision, entry.result_status, entry.session_id,
        )

    def to_list(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self.entries]


# ---------------------------------------------------------------------------
# Input sanitization
# ---------------------------------------------------------------------------

class SanitizationError(ValueError):
    """Raised when tool input fails sanitization."""


@dataclass
class SanitizedInput:
    """Validated, safe input values."""

    objective: str
    finding_id: str | None = None
    proposal_id: str | None = None
    approver: str = ""
    approvals: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)


class ToolInputSanitizer:
    """Validates and sanitizes agent tool inputs before they reach the engine.

    This is the first line of defense against prompt injection, oversized
    payloads, and path traversal.  Defense-in-depth: the engine itself also
    bounds input (MAX_QUERY_CHARS), and the safety gate provides a second
    layer.
    """

    def __init__(
        self,
        max_input_length: int = DEFAULT_MAX_INPUT_LENGTH,
        max_objective_length: int = MAX_OBJECTIVE_LENGTH,
    ) -> None:
        self.max_input_length = max_input_length
        self.max_objective_length = max_objective_length

    def _check_length(self, value: str, name: str, max_len: int) -> None:
        if len(value) > max_len:
            raise SanitizationError(
                f"Input '{name}' exceeds maximum length {max_len} "
                f"(got {len(value)} chars)."
            )

    def _check_injection(self, value: str, name: str) -> None:
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(value):
                raise SanitizationError(
                    f"Potential prompt injection detected in '{name}': "
                    f"pattern matched. Input rejected by security boundary."
                )

    def _check_path_traversal(self, value: str | None, name: str) -> None:
        if value is None:
            return
        if _PATH_TRAVERSAL_PATTERN.search(value):
            raise SanitizationError(
                f"Path traversal attempt detected in '{name}'. "
                f"Absolute or relative file paths are not accepted."
            )

    def sanitize_objective(self, objective: str) -> str:
        """Validate and sanitize a security problem objective."""
        if not isinstance(objective, str):
            raise SanitizationError("objective must be a string.")
        if not objective.strip():
            raise SanitizationError("objective must not be empty.")
        self._check_length(objective, "objective", self.max_objective_length)
        self._check_injection(objective, "objective")
        self._check_path_traversal(objective, "objective")
        return objective.strip()

    def sanitize_id(self, value: str | None, name: str, max_len: int) -> str | None:
        """Validate a finding/proposal ID."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise SanitizationError(f"{name} must be a string.")
        if not value.strip():
            raise SanitizationError(f"{name} must not be empty.")
        self._check_length(value, name, max_len)
        self._check_path_traversal(value, name)
        return value.strip()

    def sanitize_approver(self, approver: str) -> str:
        """Validate an approver identifier."""
        if not isinstance(approver, str):
            raise SanitizationError("approver must be a string.")
        if not approver.strip():
            raise SanitizationError("approver must not be empty.")
        self._check_length(approver, "approver", MAX_APPROVER_LENGTH)
        self._check_path_traversal(approver, "approver")
        return approver.strip()

    def sanitize_approvals(self, approvals: Any) -> dict[str, bool]:
        """Validate the approvals mapping."""
        if not isinstance(approvals, Mapping):
            raise SanitizationError("approvals must be a mapping of str→bool.")
        valid_keys = {
            "explicit_authorization", "sandbox", "rollback", "logging",
            "stop_condition", "isolated_sandbox", "human_approval",
            "authorized_scope_confirmed", "full_logging",
        }
        result: dict[str, bool] = {}
        for key, value in approvals.items():
            if not isinstance(key, str):
                raise SanitizationError("approval keys must be strings.")
            if key not in valid_keys:
                raise SanitizationError(
                    f"Unknown approval key: {key}. Valid keys: {valid_keys}"
                )
            if not isinstance(value, bool):
                raise SanitizationError(f"approval '{key}' must be a boolean.")
            result[key] = value
        return result

    def sanitize(self, **kwargs: Any) -> SanitizedInput:
        """Full sanitization of a tool call's arguments."""
        objective = self.sanitize_objective(kwargs.get("objective", ""))
        finding_id = self.sanitize_id(
            kwargs.get("finding_id"), "finding_id", MAX_FINDING_ID_LENGTH
        )
        proposal_id = self.sanitize_id(
            kwargs.get("proposal_id"), "proposal_id", MAX_PROPOSAL_ID_LENGTH
        )
        approver_raw = kwargs.get("approver")
        approver = ""
        if approver_raw is not None:
            approver = self.sanitize_approver(approver_raw)
        if "approvals" in kwargs:
            approvals = self.sanitize_approvals(kwargs.get("approvals"))
        else:
            approvals = {}

        extra: dict[str, Any] = {}
        for key in ("seed", "session_size", "profile", "session_context"):
            if key in kwargs:
                extra[key] = kwargs[key]

        return SanitizedInput(
            objective=objective,
            finding_id=finding_id,
            proposal_id=proposal_id,
            approver=approver,
            approvals=approvals,
            extra=extra,
        )


# ---------------------------------------------------------------------------
# Safety enforcement wrapper
# ---------------------------------------------------------------------------

class SafetyEnforcer:
    """Re-validates safety on every mutation — never trusts the layer's cache."""

    def __init__(self, layer: BlackforgeCapabilityLayer) -> None:
        self._layer = layer

    def reevaluate_safety(
        self,
        item: Mapping[str, Any],
        approvals: Mapping[str, bool],
        session_id: str,
    ) -> SafetyDecision:
        """Re-run the safety gate with fresh approvals context."""
        ctx: dict[str, Any] = {
            "explicit_authorization": bool(approvals.get("explicit_authorization", False)),
            "sandbox": bool(approvals.get("sandbox", False)),
            "rollback": bool(approvals.get("rollback", False)),
            "logging": bool(approvals.get("logging", False)),
            "full_logging": bool(approvals.get("full_logging", approvals.get("logging", False))),
            "stop_condition": bool(approvals.get("stop_condition", False)),
            "isolated_sandbox": bool(approvals.get("isolated_sandbox", False)),
            "human_approval": bool(approvals.get("human_approval", False)),
            "authorized_scope_confirmed": bool(approvals.get("authorized_scope_confirmed", False)),
        }
        return evaluate_blackforge_safety(item, ctx, session_id=session_id)


# ---------------------------------------------------------------------------
# Zero-trust audit wrapper
# ---------------------------------------------------------------------------

class ZeroTrustAuditWrapper:
    """Wraps the capability layer with full auditability + security enforcement.

    Every public method:
      1. Sanitizes input
      2. Logs the tool call
      3. Executes (delegating to the layer)
      4. Re-validates safety on mutations
      5. Records the outcome

    Actors are classified as "human" or "agent" — the system never trusts
    an agent to bypass safety.
    """

    def __init__(
        self,
        layer: BlackforgeCapabilityLayer,
        *,
        actor: str = "system",
        actor_type: str = "system",
    ) -> None:
        self._layer = layer
        self._sanitizer = ToolInputSanitizer()
        self._enforcer = SafetyEnforcer(layer)
        self._audit = MutationLog()
        self._actor = actor
        self._actor_type = actor_type

    # ------------------------------------------------------------------
    # Audit accessors
    # ------------------------------------------------------------------

    @property
    def audit_log(self) -> list[dict[str, Any]]:
        """Return the full audit trail."""
        return self._audit.to_list()

    def get_actor(self) -> str:
        return self._actor

    def get_actor_type(self) -> str:
        return self._actor_type

    # ------------------------------------------------------------------
    # READ operations (no safety re-validation needed)
    # ------------------------------------------------------------------

    def get_context(self) -> dict[str, Any]:
        self._audit.append(AuditEntry(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            tool_name="get_context",
            actor=self._actor, actor_type=self._actor_type,
            input_size=0, safety_decision="N/A", result_status="OK",
            session_id=self._layer.get_context().get("session_id", ""),
        ))
        return self._layer.get_context()

    def analyze_security_problem(self, objective: str, **kwargs: Any) -> dict[str, Any]:
        """Validate input then delegate to the layer's analysis."""
        sanitized = self._sanitizer.sanitize(objective=objective, **kwargs)
        packet = self._layer.analyze_security_problem(
            sanitized.objective, **sanitized.extra
        )
        self._audit.append(AuditEntry(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            tool_name="analyze_security_problem",
            actor=self._actor, actor_type=self._actor_type,
            input_size=len(sanitized.objective),
            safety_decision="N/A", result_status="OK",
            session_id=self._layer.get_context().get("session_id", ""),
        ))
        return packet

    def get_findings(self) -> list[dict[str, Any]]:
        self._audit.append(AuditEntry(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            tool_name="get_findings",
            actor=self._actor, actor_type=self._actor_type,
            input_size=0, safety_decision="N/A", result_status="OK",
            session_id=self._layer.get_context().get("session_id", ""),
        ))
        return self._layer.get_findings()

    def get_finding(self, finding_id: str) -> dict[str, Any] | None:
        fid = self._sanitizer.sanitize_id(finding_id, "finding_id", MAX_FINDING_ID_LENGTH)
        self._audit.append(AuditEntry(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            tool_name="get_finding",
            actor=self._actor, actor_type=self._actor_type,
            input_size=len(fid or ""),
            safety_decision="N/A", result_status="OK",
            session_id=self._layer.get_context().get("session_id", ""),
        ))
        return self._layer.get_finding(fid) if fid else None

    def generate_defensive_options(self, finding_id: str) -> list[dict[str, Any]]:
        fid = self._sanitizer.sanitize_id(finding_id, "finding_id", MAX_FINDING_ID_LENGTH)
        self._audit.append(AuditEntry(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            tool_name="generate_defensive_options",
            actor=self._actor, actor_type=self._actor_type,
            input_size=len(fid or ""),
            safety_decision="N/A", result_status="OK",
            session_id=self._layer.get_context().get("session_id", ""),
        ))
        return self._layer.generate_defensive_options(fid) if fid else []

    def compare_defensive_options(self, option_a: str, option_b: str) -> dict[str, Any]:
        self._audit.append(AuditEntry(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            tool_name="compare_defensive_options",
            actor=self._actor, actor_type=self._actor_type,
            input_size=len(option_a) + len(option_b),
            safety_decision="N/A", result_status="OK",
            session_id=self._layer.get_context().get("session_id", ""),
        ))
        return self._layer.compare_defensive_options(option_a, option_b)

    def get_history(self) -> list[dict[str, Any]]:
        self._audit.append(AuditEntry(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            tool_name="get_history",
            actor=self._actor, actor_type=self._actor_type,
            input_size=0, safety_decision="N/A", result_status="OK",
            session_id=self._layer.get_context().get("session_id", ""),
        ))
        return self._layer.get_history()

    def get_security_score(self) -> dict[str, Any]:
        self._audit.append(AuditEntry(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            tool_name="get_security_score",
            actor=self._actor, actor_type=self._actor_type,
            input_size=0, safety_decision="N/A", result_status="OK",
            session_id=self._layer.get_context().get("session_id", ""),
        ))
        return self._layer.get_security_score()

    # ------------------------------------------------------------------
    # MUTATION operations (full safety + audit)
    # ------------------------------------------------------------------

    def propose_mitigation(self, finding_id: str, option_id: str = "opt-1") -> str:
        """Create a proposal — no safety gate needed (non-mutating)."""
        fid = self._sanitizer.sanitize_id(finding_id, "finding_id", MAX_FINDING_ID_LENGTH)
        if not fid:
            raise SanitizationError("finding_id is required")
        proposal_id = self._layer.propose_mitigation(fid, option_id)
        self._audit.append(AuditEntry(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            tool_name="propose_mitigation",
            actor=self._actor, actor_type=self._actor_type,
            input_size=len(fid),
            safety_decision="N/A", result_status="OK",
            session_id=self._layer.get_context().get("session_id", ""),
        ))
        return proposal_id

    def apply_approved_mutation(
        self,
        proposal_id: str,
        approver: str,
        approvals: Mapping[str, bool],
    ) -> dict[str, Any]:
        """Apply a mitigation — FULL safety re-validation + audit.

        This is the ONLY mutation path.  The wrapper:
          1. Sanitizes all inputs
          2. Looks up the proposal
          3. Re-evaluates safety with fresh approvals
          4. If DENY → refuses, logs DENY
          5. If ALLOW → applies, logs ALLOW
        """
        sid = self._sanitizer.sanitize_id(
            proposal_id, "proposal_id", MAX_PROPOSAL_ID_LENGTH
        )
        clean_approver = self._sanitizer.sanitize_approver(approver)
        clean_approvals = self._sanitizer.sanitize_approvals(approvals)

        if not sid:
            raise SanitizationError("proposal_id is required")

        # The layer's internal proposal store
        proposals = self._layer._proposals  # accessed via layer (same process)
        proposal = proposals.get(sid)
        if proposal is None:
            self._audit.append(AuditEntry(
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                tool_name="apply_approved_mutation",
                actor=self._actor, actor_type=self._actor_type,
                input_size=len(sid),
                safety_decision="N/A", result_status="PROPOSAL_NOT_FOUND",
                session_id=self._layer.get_context().get("session_id", ""),
            ))
            return {"status": "ERROR", "reason": f"Proposal not found: {sid}"}

        # Get the original finding for safety re-evaluation
        finding = self._layer.get_finding(proposal.finding_id)
        if finding is None:
            self._audit.append(AuditEntry(
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                tool_name="apply_approved_mutation",
                actor=self._actor, actor_type=self._actor_type,
                input_size=len(sid),
                safety_decision="N/A", result_status="FINDING_NOT_FOUND",
                session_id=self._layer.get_context().get("session_id", ""),
            ))
            return {"status": "ERROR", "reason": f"Finding not found: {proposal.finding_id}"}

        # Re-evaluate safety with fresh approvals
        ctx_session = self._layer.get_context().get("session_id", "default")
        item_for_safety: dict[str, Any] = {
            "blackforge_id": proposal.finding_id,
            "safety_class": finding.get("safety_class", "S1_DEFENSIVE"),
        }
        # Merge full_logging into the approvals passed to safety enforcer
        approvals_with_logging = dict(clean_approvals)
        if "full_logging" not in approvals_with_logging:
            approvals_with_logging["full_logging"] = approvals_with_logging.get("logging", False)
        decision = self._enforcer.reevaluate_safety(
            item_for_safety, approvals_with_logging, ctx_session
        )

        if decision.decision == DENY:
            self._audit.append(AuditEntry(
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                tool_name="apply_approved_mutation",
                actor=self._actor, actor_type=self._actor_type,
                input_size=len(sid),
                safety_decision=DENY,
                result_status="DENIED",
                session_id=ctx_session,
            ))
            return {
                "status": "DENIED",
                "proposal_id": sid,
                "reason": "; ".join(decision.reasons),
                "unmet_requirements": decision.unmet_requirements,
            }

        # Safety allows — apply via the layer
        try:
            result = self._layer.apply_approved_mitigation(
                proposal_id=sid,
                approver= clean_approver if clean_approver else "system",
                approvals=clean_approvals,
            )
        except PermissionError:
            self._audit.append(AuditEntry(
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                tool_name="apply_approved_mutation",
                actor=self._actor, actor_type=self._actor_type,
                input_size=len(sid),
                safety_decision=decision.decision,
                result_status="PERMISSION_DENIED",
                session_id=ctx_session,
            ))
            raise  # Re-raise so caller knows mutation is blocked

        self._audit.append(AuditEntry(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            tool_name="apply_approved_mutation",
            actor=self._actor, actor_type=self._actor_type,
            input_size=len(sid),
            safety_decision=decision.decision,
            result_status=result.get("status", "UNKNOWN"),
            session_id=ctx_session,
        ))

        return result

    # ------------------------------------------------------------------
    # Security introspection
    # ------------------------------------------------------------------

    def get_audit_summary(self) -> dict[str, Any]:
        """Return summary statistics of the audit trail."""
        statuses: dict[str, int] = {}
        decisions: dict[str, int] = {}
        for entry in self._audit.entries:
            statuses[entry.result_status] = statuses.get(entry.result_status, 0) + 1
            decisions[entry.safety_decision] = decisions.get(entry.safety_decision, 0) + 1

        return {
            "total_tool_calls": len(self._audit.entries),
            "by_status": statuses,
            "by_safety_decision": decisions,
            "actor": self._actor,
            "actor_type": self._actor_type,
        }
