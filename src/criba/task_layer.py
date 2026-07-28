"""Task Layer — TaskDefinition & mandatory sequences (HIPERMEGAPROMPT §3).

Defines *what operation* the engine must perform on a problem, independent
of *how* (personas, ensemble, chain).  Includes both CRIBA and Blackforge
task types and their mandatory execution sequences.
"""
from __future__ import annotations

import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Task type enums
# ---------------------------------------------------------------------------

class CribaTaskType(str, Enum):
    GENERATION = "generation"
    EVALUATION = "evaluation"
    IMPROVEMENT = "improvement"
    DISRUPTION = "disruption"
    CONVERGENCE = "convergence"
    RESEARCH = "research"
    DESIGN = "design"


class BlackforgeTaskType(str, Enum):
    THREAT_MODELING = "threat_modeling"
    SECURITY_ASSESSMENT = "security_assessment"
    PENTESTING = "pentesting"
    RED_TEAM = "red_team"
    BLUE_TEAM = "blue_team"
    PURPLE_TEAM = "purple_team"
    VULN_RESEARCH = "vuln_research"
    CYBER_INNOVATION = "cyber_innovation"


# ---------------------------------------------------------------------------
# Mandatory sequences (§3.5)
# ---------------------------------------------------------------------------

CRIBA_SEQUENCE: list[str] = [
    "INTERPRET",
    "DELIMIT",
    "CARTOGRAPH",
    "DECOMPOSE",
    "SELECT",
    "GENERATE",
    "CONTRAST",
    "VALIDATE",
    "PRIORITIZE",
    "CONCLUDE",
]

BLACKFORGE_EXTENSION: list[str] = [
    "ADVERSARIALIZE",
    "CONTAIN",
    "DETECT",
    "RECOVER",
]

BLACKFORGE_SEQUENCE: list[str] = CRIBA_SEQUENCE + BLACKFORGE_EXTENSION


# ---------------------------------------------------------------------------
# TaskDefinition
# ---------------------------------------------------------------------------

class TaskDefinition(BaseModel):
    """Structured task definition (§3.2).

    Captures the exact operation the engine must execute, including
    convergence conditions, rejection conditions, and evidence requirements.
    """

    task_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    operating_mode: str = "criba"  # "criba" | "blackforge"
    task_type: str = "generation"
    primary_objective: str = ""
    secondary_objectives: list[str] = Field(default_factory=list)
    required_operations: list[str] = Field(default_factory=list)
    execution_sequence: list[str] = Field(default_factory=list)
    minimum_depth: int = 1
    exploration_width: int = 3
    convergence_conditions: list[str] = Field(default_factory=list)
    rejection_conditions: list[str] = Field(default_factory=list)
    evidence_requirements: list[str] = Field(default_factory=list)
    final_decision_required: bool = True

    # Trace
    query_element_used: str = ""
    problem_subpart_addressed: str = ""
    operator_applied: str = ""
    transformation_performed: str = ""
    evidence_considered: list[str] = Field(default_factory=list)
    evaluation_performed: str = ""
    final_status: str = "pending"


# ---------------------------------------------------------------------------
# Sequence validation
# ---------------------------------------------------------------------------

class SequenceValidation(BaseModel):
    """Result of validating a task sequence against mandatory order."""

    is_valid: bool
    current_step: str = ""
    expected_next: list[str] = Field(default_factory=list)
    completed_steps: list[str] = Field(default_factory=list)
    missing_steps: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)


def validate_sequence(
    completed_steps: list[str],
    mode: str = "criba",
) -> SequenceValidation:
    """Validate that completed steps respect the mandatory sequence.

    Parameters
    ----------
    completed_steps : list[str]
        Steps already executed, in order.
    mode : str
        ``"criba"`` or ``"blackforge"``.

    Returns
    -------
    SequenceValidation
        Whether the sequence is valid and what's expected next.
    """
    ref_seq = BLACKFORGE_SEQUENCE if mode == "blackforge" else CRIBA_SEQUENCE
    ref_set = set(ref_seq)

    # Check for unknown steps
    violations: list[str] = []
    for step in completed_steps:
        if step not in ref_set:
            violations.append(f"Unknown step '{step}' not in {mode.upper()} sequence")

    # Check ordering: each step must appear before later steps
    filtered = [s for s in completed_steps if s in ref_set]
    for i, step_a in enumerate(filtered):
        for step_b in filtered[i + 1:]:
            idx_a = ref_seq.index(step_a)
            idx_b = ref_seq.index(step_b)
            if idx_a > idx_b:
                violations.append(
                    f"Step '{step_a}' (index {idx_a}) appears after '{step_b}' "
                    f"(index {idx_b}) — order violated"
                )

    # Determine expected next
    completed_set = set(filtered)
    expected_next: list[str] = []
    missing: list[str] = []
    for step in ref_seq:
        if step not in completed_set:
            missing.append(step)
            if not expected_next:
                expected_next.append(step)

    return SequenceValidation(
        is_valid=len(violations) == 0,
        current_step=filtered[-1] if filtered else "",
        expected_next=expected_next,
        completed_steps=filtered,
        missing_steps=missing,
        violations=violations,
    )


# ---------------------------------------------------------------------------
# Task builder
# ---------------------------------------------------------------------------

def define_task(
    query: str,
    context: dict[str, Any] | None = None,
    task_type: str = "generation",
    mode: str = "criba",
) -> TaskDefinition:
    """Create a TaskDefinition from query context (§3.2).

    Parameters
    ----------
    query : str
        Original user query.
    context : dict, optional
        Pre-built context (from context_layer.build_context).
    task_type : str
        One of the CribaTaskType or BlackforgeTaskType values.
    mode : str
        ``"criba"`` or ``"blackforge"``.
    """
    sequence = BLACKFORGE_SEQUENCE if mode == "blackforge" else CRIBA_SEQUENCE

    return TaskDefinition(
        operating_mode=mode,
        task_type=task_type,
        primary_objective=f"Process query via {task_type} in {mode} mode",
        required_operations=[task_type],
        execution_sequence=sequence,
        convergence_conditions=[
            "Ideas are structurally distinct",
            "Mechanisms are specific, not generic",
            "Risks are acknowledged",
        ],
        rejection_conditions=[
            "No mechanism explained",
            "Generic 'use AI' proposal",
            "No evidence or traceability",
            "Cosmetic diversity only",
        ],
        evidence_requirements=[
            "Query anchor present",
            "Operator justified",
            "Mechanism translates to components",
        ],
        query_element_used=query[:200],
    )
