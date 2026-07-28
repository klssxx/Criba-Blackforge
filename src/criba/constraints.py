"""Constraints Layer — Knowledge/Novelty classification & rejection rules (§4).

Defines what the engine *must not* do, what conditions it must respect,
and how to classify the epistemic status of claims.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Knowledge status (§4.2)
# ---------------------------------------------------------------------------

class KnowledgeStatus(str, Enum):
    CONFIRMED_FACT = "confirmed_fact"
    SOURCE_SUPPORTED = "source_supported"
    INFERENCE = "inference"
    ASSUMPTION = "assumption"
    SPECULATION = "speculation"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Novelty status (§4.2)
# ---------------------------------------------------------------------------

class NoveltyStatus(str, Enum):
    KNOWN = "known"
    INCREMENTAL = "incremental"
    UNCOMMON_COMBINATION = "uncommon_combination"
    POTENTIALLY_NOVEL = "potentially_novel"
    UNVERIFIED_NOVELTY = "unverified_novelty"


# ---------------------------------------------------------------------------
# Finding confidence (§4.3)
# ---------------------------------------------------------------------------

class FindingConfidence(str, Enum):
    HYPOTHESIS = "hypothesis"
    SUSPECTED = "suspected"
    PARTIALLY_VALIDATED = "partially_validated"
    REPRODUCIBLE = "reproducible"
    CONFIRMED = "confirmed"
    NOT_REPRODUCIBLE = "not_reproducible"
    FALSE_POSITIVE = "false_positive"


# ---------------------------------------------------------------------------
# ConstraintSet
# ---------------------------------------------------------------------------

class ConstraintSet(BaseModel):
    """Collection of active constraints for a context (§4.1)."""

    # General CRIBA constraints
    no_invent_information: bool = True
    no_confuse_novelty_with_ignorance: bool = True
    no_ideas_without_mechanism: bool = True
    no_default_optimism: bool = True
    no_unnecessary_complexity: bool = True
    no_premature_convergence: bool = True
    no_cosmetic_diversity: bool = True
    no_cover_everything: bool = True

    # Quality constraints (§4.4)
    grounded_in_query: bool = True
    mechanism_explained: bool = True
    assumptions_visible: bool = True
    uncertainties_visible: bool = True
    alternatives_compared: bool = True
    risks_included: bool = True
    priority_declared: bool = True
    traceability_available: bool = True

    # Blackforge-specific constraints (§4.3)
    # These are REQUIREMENTS that must be satisfied, NOT declarations of state.
    # Setting them to True means "this field MUST be present in the output",
    # NOT "this has been verified".
    require_authorization: bool = False
    require_protected_asset: bool = False
    require_threat_actor: bool = False
    require_attack_surface: bool = False
    require_security_property: bool = False
    require_evidence_status: bool = False
    require_bypass_analysis: bool = False
    require_residual_risk: bool = False
    require_safe_validation: bool = False

    # User-provided extra constraints
    extra_constraints: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Validation results
# ---------------------------------------------------------------------------

class ConstraintViolation(BaseModel):
    """A single constraint violation."""

    rule: str
    description: str
    severity: str = "warning"  # "warning" | "error" | "critical"


class ConstraintValidation(BaseModel):
    """Result of validating an idea against constraints."""

    passes: bool
    violations: list[ConstraintViolation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Classification functions
# ---------------------------------------------------------------------------

def classify_knowledge(claim: str, *, sources: list[str] | None = None) -> KnowledgeStatus:
    """Classify the epistemic status of a claim using linguistic signals (§4.2).

    NOTE: This is a heuristic based on claim wording and source presence.
    It does NOT independently verify factual accuracy. A claim containing
    "demostrado" with sources is classified as CONFIRMED_FACT based on
    stated signals, not independent verification. Downstream consumers
    should apply additional validation when high-stakes decisions depend
    on CONFIRMED status.

    Parameters
    ----------
    claim : str
        The claim to classify.
    sources : list[str], optional
        Available source references.  Presence bumps status upward.
    """
    c = claim.lower()
    has_sources = bool(sources)

    # Strong negative indicators (always checked first)
    if any(w in c for w in ("inventado", "imaginado", "supongo que", "tal vez")):
        return KnowledgeStatus.SPECULATION
    if any(w in c for w in ("no sé", "desconocido", "sin datos")):
        return KnowledgeStatus.UNKNOWN

    # Check content-level indicators BEFORE source presence
    # Inference indicators: hedging language
    if any(w in c for w in ("probablemente", "sugiere", "indica", "podría")):
        return KnowledgeStatus.INFERENCE if has_sources else KnowledgeStatus.ASSUMPTION

    # Assumption indicators: belief/estimation language
    if any(w in c for w in ("asumimos", "creemos", "estimamos")):
        return KnowledgeStatus.ASSUMPTION

    # Strong positive with sources
    if has_sources and any(w in c for w in ("demostrado", "verificado", "medido")):
        return KnowledgeStatus.CONFIRMED_FACT
    if has_sources:
        return KnowledgeStatus.SOURCE_SUPPORTED

    return KnowledgeStatus.ASSUMPTION


def classify_novelty(
    claim: str,
    *,
    known_solutions: list[str] | None = None,
) -> NoveltyStatus:
    """Classify the novelty status of a claim (§4.2).

    Parameters
    ----------
    claim : str
        The claim to classify.
    known_solutions : list[str], optional
        Already-known solutions for comparison.
    """
    c = claim.lower()
    known = [s.lower() for s in (known_solutions or [])]

    # Check if it matches known solutions
    for sol in known:
        if sol and sol in c:
            return NoveltyStatus.KNOWN

    if any(w in c for w in ("incremento", "añad", "mejorar ligeramente", "extender")):
        return NoveltyStatus.INCREMENTAL
    if any(w in c for w in ("combinación", "mezcla", "cross", "interdisciplinar")):
        return NoveltyStatus.UNCOMMON_COMBINATION
    if any(w in c for w in ("nunca se ha hecho", "sin precedente", "primera vez")):
        return NoveltyStatus.UNVERIFIED_NOVELTY

    return NoveltyStatus.POTENTIALLY_NOVEL


# ---------------------------------------------------------------------------
# Constraint builder
# ---------------------------------------------------------------------------

def build_constraints(
    context: dict[str, Any] | None = None,
    task: dict[str, Any] | None = None,
    mode: Literal["criba", "blackforge"] = "criba",
) -> ConstraintSet:
    """Build a ConstraintSet from context and task information.

    Parameters
    ----------
    context : dict, optional
        The InnovationContext as a dict.
    task : dict, optional
        The TaskDefinition as a dict.
    mode : str
        ``"criba"`` or ``"blackforge"``.  Unknown modes raise ValueError.
    """
    if mode not in ("criba", "blackforge"):
        raise ValueError(f"Unknown mode '{mode}'; expected 'criba' or 'blackforge'")

    constraints = ConstraintSet()

    if mode == "blackforge":
        # These are REQUIREMENTS: the output/context must demonstrate these fields.
        # They do NOT declare that authorization exists — they demand proof.
        constraints.require_authorization = True
        constraints.require_protected_asset = True
        constraints.require_threat_actor = True
        constraints.require_attack_surface = True
        constraints.require_security_property = True
        constraints.require_evidence_status = True
        constraints.require_bypass_analysis = True
        constraints.require_residual_risk = True
        constraints.require_safe_validation = True

    # Add user constraints from context
    ctx = context or {}
    if ctx.get("constraints"):
        constraints.extra_constraints = list(ctx["constraints"])

    return constraints


# ---------------------------------------------------------------------------
# Idea validation
# ---------------------------------------------------------------------------

def validate_idea_against_constraints(
    idea: dict[str, Any],
    constraints: ConstraintSet,
    mode: Literal["criba", "blackforge"] = "criba",
) -> ConstraintValidation:
    """Validate a single idea against the active constraint set.

    Implements the rejection rules from §4.2 and §4.5.

    Parameters
    ----------
    idea : dict
        The idea to validate.  Expected keys: title, mechanism,
        description, risks, alternatives, etc.
    constraints : ConstraintSet
        Active constraints.
    mode : str
        ``"criba"`` or ``"blackforge"``.  Unknown modes raise ValueError.
    """
    if mode not in ("criba", "blackforge"):
        raise ValueError(f"Unknown mode '{mode}'; expected 'criba' or 'blackforge'")
    violations: list[ConstraintViolation] = []
    warnings: list[str] = []

    # --- CRIBA constraints ---
    if constraints.no_invent_information:
        if idea.get("invented_data"):
            violations.append(ConstraintViolation(
                rule="no_invent_information",
                description="Idea contains invented data or sources",
                severity="critical",
            ))

    if constraints.no_ideas_without_mechanism:
        mechanism = idea.get("mechanism", "")
        if not mechanism or mechanism.lower() in ("usar ia", "usar blockchain", "automatizar", ""):
            violations.append(ConstraintViolation(
                rule="no_ideas_without_mechanism",
                description="Idea lacks a specific mechanism — generic placeholder only",
                severity="error",
            ))

    if constraints.no_default_optimism:
        if not idea.get("risks") and not idea.get("principal_risk"):
            warnings.append("No risks acknowledged — possible default optimism")

    if constraints.no_cosmetic_diversity:
        if idea.get("cosmetic_only"):
            violations.append(ConstraintViolation(
                rule="no_cosmetic_diversity",
                description="Idea is cosmetic variation, not structural difference",
                severity="error",
            ))

    if constraints.grounded_in_query:
        if not idea.get("problem_anchor") and not idea.get("query_element_used"):
            warnings.append("Idea not anchored to specific query element")

    if constraints.mechanism_explained:
        mech = idea.get("mechanism", "")
        if mech and len(str(mech)) < 10:
            warnings.append("Mechanism description too short to be meaningful")

    if constraints.assumptions_visible:
        if not idea.get("assumptions") and not idea.get("known_risks"):
            warnings.append("Assumptions not made visible")

    if constraints.risks_included:
        if not idea.get("risks") and not idea.get("principal_risk") and not idea.get("known_risks"):
            warnings.append("No risk analysis included")

    # --- Blackforge-specific ---
    if mode == "blackforge":
        if constraints.require_authorization and not idea.get("authorization_status"):
            violations.append(ConstraintViolation(
                rule="require_authorization",
                description="Authorization status not declared — Blackforge requires explicit authorization proof",
                severity="critical",
            ))
        if constraints.require_bypass_analysis and not idea.get("bypass"):
            warnings.append("Bypass path not analyzed — Blackforge requires bypass consideration")
        if constraints.require_residual_risk and not idea.get("residual_risk"):
            warnings.append("Residual risk not declared — Blackforge requires residual risk declaration")

    passes = not any(v.severity == "critical" for v in violations) and \
             not any(v.severity == "error" for v in violations)

    return ConstraintValidation(
        passes=passes,
        violations=violations,
        warnings=warnings,
    )
