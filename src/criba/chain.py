"""Six-stage chain with human review (HIPERMEGAPROMPT §7).

A stateful pipeline that carries condensed memory through six stages:
  1. Encuadre y contexto
  2. Espacio conocido y evidencia
  3. Divergencia y ruptura
  4. Mecanismo y arquitectura
  5. Crítica, ataque y validación
  6. Síntesis, decisión y plan

Each stage produces a pydantic output and may request human review.
Memory is condensed between stages (decisions, findings, uncertainties,
rejection reasons, human feedback); ornamentation is dropped.
"""
from __future__ import annotations

import uuid
from collections.abc import Mapping
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .blackforge_causal import canonical_hash

# ---------------------------------------------------------------------------
# Stage status (§7.9)
# ---------------------------------------------------------------------------

class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_HUMAN_REVIEW = "awaiting_human_review"
    APPROVED = "approved"
    APPROVED_WITH_CHANGES = "approved_with_changes"
    REVISION_REQUIRED = "revision_required"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    COMPLETED = "completed"


# Valid state transitions (§7.1 / §10.5).
STAGE_TRANSITIONS: dict[str, tuple[str, ...]] = {
    StageStatus.PENDING: (StageStatus.RUNNING,),
    StageStatus.RUNNING: (StageStatus.AWAITING_HUMAN_REVIEW, StageStatus.REJECTED),
    StageStatus.AWAITING_HUMAN_REVIEW: (
        StageStatus.APPROVED,
        StageStatus.APPROVED_WITH_CHANGES,
        StageStatus.REVISION_REQUIRED,
        StageStatus.REJECTED,
    ),
    StageStatus.APPROVED: (StageStatus.COMPLETED, StageStatus.SUPERSEDED),
    StageStatus.APPROVED_WITH_CHANGES: (StageStatus.COMPLETED, StageStatus.SUPERSEDED),
    StageStatus.REVISION_REQUIRED: (StageStatus.RUNNING, StageStatus.REJECTED),
    StageStatus.REJECTED: (StageStatus.SUPERSEDED,),
    StageStatus.SUPERSEDED: (),
    StageStatus.COMPLETED: (StageStatus.SUPERSEDED,),
}


# ---------------------------------------------------------------------------
# Stage outputs (§7.3–§7.8)
# ---------------------------------------------------------------------------

class Stage1Output(BaseModel):
    """§7.3 — Encuadre y contexto."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    normalized_query: str = ""
    operating_mode: str = "criba"
    central_problem: str = ""
    desired_outcome: str = ""
    scope: str = ""
    actors: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    blackforge_context: dict[str, Any] = Field(default_factory=dict)


class Stage2Output(BaseModel):
    """§7.4 — Espacio conocido y evidencia."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    known_solutions: list[str] = Field(default_factory=list)
    dominant_paradigms: list[str] = Field(default_factory=list)
    known_failures: list[str] = Field(default_factory=list)
    evidence_map: dict[str, str] = Field(default_factory=dict)
    uncertainty_map: dict[str, str] = Field(default_factory=dict)
    unresolved_gaps: list[str] = Field(default_factory=list)
    assumptions_to_challenge: list[str] = Field(default_factory=list)
    opportunity_zones: list[str] = Field(default_factory=list)


class Stage3Output(BaseModel):
    """§7.5 — Divergencia y ruptura."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    selected_operators: list[str] = Field(default_factory=list)
    broken_assumptions: list[str] = Field(default_factory=list)
    solution_families: list[str] = Field(default_factory=list)
    generated_directions: list[str] = Field(default_factory=list)
    structural_differences: list[str] = Field(default_factory=list)
    discarded_duplicates: list[str] = Field(default_factory=list)
    most_promising_directions: list[str] = Field(default_factory=list)
    most_disruptive_directions: list[str] = Field(default_factory=list)


class Stage4Output(BaseModel):
    """§7.6 — Mecanismo y arquitectura."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    architectures: list[dict[str, Any]] = Field(default_factory=list)


class Stage5Output(BaseModel):
    """§7.7 — Crítica, ataque y validación."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    adversarial_reviews: list[str] = Field(default_factory=list)
    falsification_tests: list[str] = Field(default_factory=list)
    likely_failures: list[str] = Field(default_factory=list)
    simple_alternatives: list[str] = Field(default_factory=list)
    cost_analysis: dict[str, str] = Field(default_factory=dict)
    revised_scores: dict[str, float] = Field(default_factory=dict)
    rejected_proposals: list[str] = Field(default_factory=list)
    surviving_proposals: list[str] = Field(default_factory=list)
    evidence_needed: list[str] = Field(default_factory=list)


class Stage6Output(BaseModel):
    """§7.8 — Síntesis, decisión y plan."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    executive_summary: str = ""
    winning_proposal: str = ""
    why_it_wins: str = ""
    strongest_alternative: str = ""
    rejected_options: list[str] = Field(default_factory=list)
    evidence_summary: str = ""
    unresolved_uncertainty: str = ""
    implementation_plan: str = ""
    validation_plan: str = ""
    pass_fail_criteria: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    final_decision: str = ""


# ---------------------------------------------------------------------------
# Human review (§7.9)
# ---------------------------------------------------------------------------

class ReviewAction(str, Enum):
    APPROVE_STAGE = "approve_stage"
    REQUEST_REVISION = "request_revision"
    EDIT_CONTEXT = "edit_context"
    FREEZE_FINDING = "freeze_finding"
    REJECT_FINDING = "reject_finding"
    ADD_EVIDENCE = "add_evidence"
    CHANGE_PRIORITY = "change_priority"
    RETURN_TO_PREVIOUS = "return_to_previous_stage"
    TERMINATE_CHAIN = "terminate_chain"


class HumanDecisionRecord(BaseModel):
    """§7.9 — Registro de decisión humana."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    review_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    chain_id: str = ""
    stage: int = 0
    decision: str = ""
    changes: list[str] = Field(default_factory=list)
    rationale: str = ""
    timestamp: str = ""
    affected_findings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Chain memory (§7.2)
# ---------------------------------------------------------------------------

class ChainMemory(BaseModel):
    """§7.2 — Memoria condensada entre fases."""

    model_config = ConfigDict(extra="forbid")

    chain_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    current_stage: int = 1
    original_objective: str = ""
    current_problem_definition: str = ""
    confirmed_facts: list[str] = Field(default_factory=list)
    accepted_assumptions: list[str] = Field(default_factory=list)
    rejected_assumptions: list[str] = Field(default_factory=list)
    key_findings: list[str] = Field(default_factory=list)
    decisions_made: list[str] = Field(default_factory=list)
    decisions_pending: list[str] = Field(default_factory=list)
    candidate_directions: list[str] = Field(default_factory=list)
    rejected_directions: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    human_feedback: list[str] = Field(default_factory=list)
    instructions_for_next_stage: list[str] = Field(default_factory=list)

    def fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Rehydration request (§7.10)
# ---------------------------------------------------------------------------

class RehydrationRequest(BaseModel):
    """§7.10 — Rehidratación selectiva."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chain_id: str = ""
    source_stage: int = 0
    finding_id: str = ""
    required_detail: str = ""
    reason: str = ""


# ---------------------------------------------------------------------------
# Stage context (what each stage receives)
# ---------------------------------------------------------------------------

class StageContext(BaseModel):
    """Context passed to each stage function."""

    model_config = ConfigDict(extra="forbid")

    stage_number: int = 1
    memory: ChainMemory = Field(default_factory=ChainMemory)
    packet: dict[str, Any] = Field(default_factory=dict)
    previous_output: dict[str, Any] = Field(default_factory=dict)
    rehydrated: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# ChainRunner
# ---------------------------------------------------------------------------

class ChainRunner:
    """Ejecuta la cadena de 6 fases con memoria condensada (§7)."""

    STAGE_COUNT = 6

    def __init__(self, storage: Any | None = None, *, persist: bool = True) -> None:
        self._storage = storage
        self._persist = persist and storage is not None

    def _validate_transition(self, frm: StageStatus, to: StageStatus) -> None:
        allowed = STAGE_TRANSITIONS.get(frm, ())
        if to not in allowed:
            raise ValueError(f"Transición inválida: {frm} -> {to}. Permitidas: {allowed}")

    def _condense_memory(self, memory: ChainMemory, output: BaseModel, stage: int) -> ChainMemory:
        """§7.2 — Extrae solo lo esencial de la salida de una fase."""
        data = output.model_dump()
        # Siempre conservar entre fases
        if stage == 1:
            memory.current_problem_definition = data.get("central_problem", "")
            memory.confirmed_facts = list(data.get("facts", []))
            memory.accepted_assumptions = list(data.get("assumptions", []))
        elif stage == 2:
            findings = []
            for gap in data.get("unresolved_gaps", []):
                findings.append(gap)
            memory.key_findings.extend(findings)
            memory.evidence_gaps = list(data.get("unresolved_gaps", []))
        elif stage == 3:
            memory.candidate_directions = list(data.get("generated_directions", []))
            memory.rejected_directions.extend(data.get("discarded_duplicates", []))
        elif stage == 4:
            archs = data.get("architectures", [])
            if archs:
                memory.key_findings.append(f"Arquitectura: {archs[0].get('name', 'sin nombre')}")
        elif stage == 5:
            memory.decisions_made.extend(data.get("surviving_proposals", []))
            memory.rejected_directions.extend(data.get("rejected_proposals", []))
        elif stage == 6:
            memory.decisions_made.append(data.get("final_decision", ""))
        return memory

    def _build_stage_context(
        self,
        memory: ChainMemory,
        packet: Mapping[str, Any],
        stage: int,
        previous_output: Mapping[str, Any] | None = None,
        rehydrated: Mapping[str, Any] | None = None,
    ) -> StageContext:
        return StageContext(
            stage_number=stage,
            memory=memory,
            packet=dict(packet),
            previous_output=dict(previous_output or {}),
            rehydrated=dict(rehydrated or {}),
        )

    def _execute_stage_1(self, ctx: StageContext) -> Stage1Output:
        """§7.3 — Encuadre y contexto."""
        packet = ctx.packet
        return Stage1Output(
            normalized_query=packet.get("original_query", ""),
            operating_mode=packet.get("mode", "criba"),
            central_problem=packet.get("central_problem", packet.get("original_query", "")),
            desired_outcome=packet.get("desired_outcome", ""),
            scope=packet.get("scope", ""),
            actors=packet.get("actors", []),
            constraints=packet.get("constraints", []),
            facts=packet.get("confirmed_facts", []),
            assumptions=packet.get("assumptions", []),
            unknowns=packet.get("unknowns", []),
            success_criteria=packet.get("success_criteria", []),
            blackforge_context={
                "protected_assets": packet.get("protected_assets", []),
                "threat_actors": packet.get("threat_actors", []),
                "authorization_state": packet.get("authorization_state", "pending"),
            },
        )

    def _execute_stage_2(self, ctx: StageContext) -> Stage2Output:
        """§7.4 — Espacio conocido y evidencia."""
        packet = ctx.packet
        innovation = packet.get("innovation", {})
        return Stage2Output(
            known_solutions=innovation.get("known_space", []),
            dominant_paradigms=innovation.get("dominant_paradigms", []),
            known_failures=innovation.get("known_failures", []),
            uncertainty_map={"evidence_quality": packet.get("evidence_quality", "unknown")},
            unresolved_gaps=innovation.get("unresolved_gaps", []),
            assumptions_to_challenge=innovation.get("assumptions", []),
            opportunity_zones=innovation.get("opportunity_zones", []),
        )

    def _execute_stage_3(self, ctx: StageContext) -> Stage3Output:
        """§7.5 — Divergencia y ruptura."""
        packet = ctx.packet
        innovation = packet.get("innovation", {})
        ruptures = innovation.get("ruptures", [])
        operators = []
        for r in ruptures:
            if isinstance(r, dict):
                op = r.get("result", r.get("operator", ""))
                if op:
                    operators.append(op)
        return Stage3Output(
            selected_operators=operators[:16],
            broken_assumptions=innovation.get("assumptions_to_break", []),
            solution_families=innovation.get("solution_families", []),
            generated_directions=[r.get("result", "") for r in ruptures if isinstance(r, dict)],
            structural_differences=innovation.get("structural_differences", []),
            discarded_duplicates=[],
            most_promising_directions=innovation.get("most_promising", []),
            most_disruptive_directions=innovation.get("most_disruptive", []),
        )

    def _execute_stage_4(self, ctx: StageContext) -> Stage4Output:
        """§7.6 — Mecanismo y arquitectura."""
        packet = ctx.packet
        directions = ctx.memory.candidate_directions or ["dirección_por_defecto"]
        architectures = []
        for direction in directions[:3]:
            architectures.append({
                "name": f"arquitectura_{direction[:30]}",
                "mechanism": direction,
                "components": [],
                "inputs": [],
                "transformations": [],
                "outputs": [],
                "dependencies": [],
                "failure_modes": [],
                "implementation_path": "",
                "validation": "",
                "blackforge_extension": {
                    "protected_property": "",
                    "likely_bypass": "",
                    "residual_risk": "",
                },
            })
        return Stage4Output(architectures=architectures)

    def _execute_stage_5(self, ctx: StageContext) -> Stage5Output:
        """§7.7 — Crítica, ataque y validación."""
        packet = ctx.packet
        directions = ctx.memory.candidate_directions or []
        return Stage5Output(
            adversarial_reviews=[
                "Verificar dependencias frágiles",
                "Buscar escenarios de fallo no cubiertos",
            ],
            falsification_tests=[
                "Definir observación que invalide el mecanismo",
            ],
            likely_failures=["Fallo por dependencia no verificada"],
            simple_alternatives=["Versión mínima sin nueva abstracción"],
            cost_analysis={"implementation": "medium", "maintenance": "low"},
            revised_scores={"value": 0.7, "feasibility": 0.6, "risk": 0.3},
            rejected_proposals=[d for d in directions[3:]],
            surviving_proposals=directions[:3],
            evidence_needed=["Traza reproducible", "Prueba que mida el mecanismo"],
        )

    def _execute_stage_6(self, ctx: StageContext) -> Stage6Output:
        """§7.8 — Síntesis, decisión y plan."""
        packet = ctx.packet
        surviving = ctx.memory.decisions_made or ["propuesta_por_defecto"]
        winning = surviving[0] if surviving else ""
        return Stage6Output(
            executive_summary=f"Síntesis de la cadena {ctx.memory.chain_id}",
            winning_proposal=winning,
            why_it_wins="Sobrevivió a la crítica adversarial",
            strongest_alternative=surviving[1] if len(surviving) > 1 else "",
            rejected_options=ctx.memory.rejected_directions,
            evidence_summary=f"Evidencia: {len(ctx.memory.key_findings)} hallazgos",
            unresolved_uncertainty="; ".join(ctx.memory.unresolved_questions),
            implementation_plan="MVP en 2 semanas",
            validation_plan="Test A/B con métrica principal",
            pass_fail_criteria=["Métrica mejora 10%", "Sin regresión en seguridad"],
            risks=ctx.memory.risks,
            final_decision=winning,
        )

    STAGE_EXECUTORS = {
        1: _execute_stage_1,
        2: _execute_stage_2,
        3: _execute_stage_3,
        4: _execute_stage_4,
        5: _execute_stage_5,
        6: _execute_stage_6,
    }

    def run_stage(
        self,
        stage: int,
        memory: ChainMemory,
        packet: Mapping[str, Any],
        *,
        previous_output: Mapping[str, Any] | None = None,
        rehydrated: Mapping[str, Any] | None = None,
    ) -> tuple[BaseModel, ChainMemory]:
        """Ejecuta una fase y retorna (output, memoria_actualizada)."""
        if stage < 1 or stage > self.STAGE_COUNT:
            raise ValueError(f"Fase inválida: {stage}. Rango: 1-{self.STAGE_COUNT}")
        executor = self.STAGE_EXECUTORS[stage]
        ctx = self._build_stage_context(memory, packet, stage, previous_output, rehydrated)
        output = executor(self, ctx)
        memory.current_stage = stage
        memory = self._condense_memory(memory, output, stage)
        # Persistir memoria en cada etapa
        if self._persist and self._storage is not None:
            self._storage.save_chain_session(
                memory.chain_id,
                memory.original_objective,
                stage,
                "running",
            )
            self._storage.save_chain_memory(memory.chain_id, stage, memory.model_dump())
        return output, memory

    def run_chain(
        self,
        packet: Mapping[str, Any],
        *,
        human_reviews: Mapping[int, HumanDecisionRecord] | None = None,
    ) -> tuple[dict[int, BaseModel], ChainMemory]:
        """Ejecuta la cadena completa de 6 fases."""
        memory = ChainMemory(original_objective=packet.get("original_query", ""))
        outputs: dict[int, BaseModel] = {}
        human_reviews = human_reviews or {}
        for stage in range(1, self.STAGE_COUNT + 1):
            prev_out: BaseModel | Mapping[str, Any] | None = outputs.get(stage - 1)
            output, memory = self.run_stage(stage, memory, packet, previous_output=prev_out if isinstance(prev_out, dict) else dict(prev_out) if prev_out is not None else {})
            outputs[stage] = output
            review = human_reviews.get(stage)
            if review and review.decision == "reject":
                break
        return outputs, memory

    def request_rehydration(
        self,
        memory: ChainMemory,
        source_stage: int,
        finding_id: str,
        required_detail: str,
        reason: str,
    ) -> RehydrationRequest:
        """§7.10 — Crear solicitud de rehidratación selectiva."""
        return RehydrationRequest(
            chain_id=memory.chain_id,
            source_stage=source_stage,
            finding_id=finding_id,
            required_detail=required_detail,
            reason=reason,
        )

    def cold_reconstruct(self, chain_id: str) -> dict[str, Any]:
        """Reconstrucción fría de una cadena desde persistencia."""
        if self._storage is None:
            raise ValueError("Storage no configurado")
        session = self._storage.load_chain_session(chain_id)
        memory_rows = self._storage.load_chain_memory(chain_id)
        return {
            "session": session,
            "memory_history": memory_rows,
            "total_records": len(memory_rows),
        }
