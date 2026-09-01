"""Hybrid orchestrator — end-to-end pipeline integration.

Connects ensemble (P3) → chain (P4) → adversarial (P5) in a single flow
with shared memory, logging (P8), and metrics (P10).

This is the accumulation loop made operational:
    ideas → ensemble → chain → adversarial → knowledge → better ideas

When semantic enhancement is enabled (``enhance_semantics=True``), the pipeline
also runs the local LLM to:
- Synthesize pipeline findings into coherent executive summary and seeds
- Generate new idea proposals for the next evolution cycle
"""
from __future__ import annotations

import json
import time
import uuid
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .adversarial_self import (
    AdversarialPass,
    AdversarialSelfReinforcement,
    ThesisPass,
    ThesisResolution,
)
from .chain import ChainMemory, ChainRunner, Stage6Output
from .ensemble import EnsembleSynthesis, run_ensemble
from .latency import GenerationBudget
from .logging import EventCategory, LogEmitter, LogProfile
from .metrics import GenerationMetrics, MetricsCollector, ProcessMetrics, ResultMetrics
from .storage import Storage

# ---------------------------------------------------------------------------
# Hybrid result
# ---------------------------------------------------------------------------

class HybridResult(BaseModel):
    """Complete output of the hybrid pipeline."""

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    ensemble: EnsembleSynthesis | None = None
    chain_outputs: dict[int, Any] = Field(default_factory=dict)
    chain_memory: ChainMemory | None = None
    thesis: ThesisPass | None = None
    adversarial: AdversarialPass | None = None
    resolution: ThesisResolution | None = None
    final_recommendation: str = ""
    final_confidence: str = "hypothesis"
    pipeline_stages_completed: list[str] = Field(default_factory=list)
    total_duration_ms: float = 0.0
    error: str | None = None
    # Semantic enhancement fields (populated when enhance_semantics=True)
    semantic_summary: str = ""
    semantic_seeds: list[dict[str, str]] = Field(default_factory=list)
    semantic_metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Hybrid orchestrator
# ---------------------------------------------------------------------------

class HybridOrchestrator:
    """Runs the full CRIBA pipeline: ensemble -> chain -> adversarial."""

    def __init__(
        self,
        storage: Storage | None = None,
        *,
        enable_logging: bool = True,
        enable_metrics: bool = True,
        budget: GenerationBudget | None = None,
    ) -> None:
        self.storage = storage or Storage()
        self.enable_logging = enable_logging
        self.enable_metrics = enable_metrics
        self.budget = budget or GenerationBudget()
        self._log_emitter: LogEmitter | None = None
        self._metrics = MetricsCollector()

    def _ensure_logger(self, session_id: str) -> LogEmitter | None:
        if not self.enable_logging:
            return None
        if self._log_emitter is None:
            self._log_emitter = LogEmitter(
                self.storage,
                session_id=session_id,
                profile=LogProfile.STANDARD,
            )
        return self._log_emitter

    def _log(
        self,
        event_type: str,
        payload: Mapping[str, Any],
        category: EventCategory = EventCategory.EVENT,
        **kwargs: Any,
    ) -> None:
        emitter = self._log_emitter
        if emitter is None:
            return
        emitter.emit(
            event_type=event_type,
            category=category,
            payload=payload,
            **kwargs,
        )

    def _seed_chain_memory_from_ensemble(
        self, memory: ChainMemory, ensemble: EnsembleSynthesis
    ) -> ChainMemory:
        """Feed ensemble synthesis into chain memory."""
        memory.current_problem_definition = ensemble.shared_problem_definition
        # Seed candidate directions from ensemble.
        memory.candidate_directions = list(ensemble.candidate_solutions)
        memory.rejected_directions = list(ensemble.rejected_solutions)
        # Seed key findings.
        for agreement in ensemble.strongest_agreements:
            memory.key_findings.append(
                f"Agreement: {agreement.finding} ({', '.join(agreement.supporting_personas)})"
            )
        for emergent in ensemble.emergent_findings:
            memory.key_findings.append(f"Emergent: {emergent.resulting_finding}")
        # Seed disagreements as unresolved questions.
        for disagreement in ensemble.substantive_disagreements:
            memory.unresolved_questions.append(
                f"Disagreement ({disagreement.category}): {disagreement.topic}"
            )
        # Seed minority report as human feedback.
        if ensemble.minority_report:
            memory.human_feedback.append(
                f"Minority: {ensemble.minority_report.disagreement}"
            )
        return memory

    def _build_adversarial_packet(
        self,
        chain_output: Stage6Output,
        ensemble: EnsembleSynthesis,
    ) -> dict[str, Any]:
        """Build packet for adversarial self-reinforcement from chain output."""
        return {
            "central_problem": chain_output.executive_summary,
            "thesis": chain_output.winning_proposal,
            "causal_mechanism": chain_output.why_it_wins,
            "expected_value": chain_output.evidence_summary,
            "assumptions": chain_output.risks,
            "confirmed_facts": [chain_output.evidence_summary] if chain_output.evidence_summary else [],
            "conflicting_evidence": [chain_output.unresolved_uncertainty] if chain_output.unresolved_uncertainty else [],
            "implementation_plan": chain_output.implementation_plan,
            "success_criteria": chain_output.pass_fail_criteria,
            "risks": chain_output.risks,
            "confidence": chain_output.final_decision and "confirmed" or "hypothesis",
        }

    def _build_synthesis_context(self, result: HybridResult) -> dict[str, Any]:
        """Build a compact context dict for the semantic synthesis call."""
        ctx: dict[str, Any] = {
            "pipeline_results": {
                "stages_completed": result.pipeline_stages_completed,
                "final_confidence": result.final_confidence,
                "final_recommendation": result.final_recommendation,
            }
        }
        # Add ensemble findings
        if result.ensemble:
            ctx["ensemble"] = {
                "shared_problem": result.ensemble.shared_problem_definition,
                "agreements": [
                    {"finding": a.finding, "confidence": a.confidence_gain}
                    for a in result.ensemble.strongest_agreements[:5]
                ],
                "emergent_findings": [
                    {"finding": e.resulting_finding, "implication": e.practical_implication}
                    for e in result.ensemble.emergent_findings[:3]
                ],
                "disagreements": [
                    {"topic": d.topic, "category": d.category}
                    for d in result.ensemble.substantive_disagreements[:3]
                ],
                "candidate_solutions": list(result.ensemble.candidate_solutions)[:6],
            }
        # Add adversarial verdict
        if result.resolution:
            ctx["adversarial"] = {
                "verdict": result.resolution.final_status,
                "survived": list(result.resolution.survived_challenges)[:4],
                "failed": list(result.resolution.failed_challenges)[:4],
                "evidence_required": result.resolution.evidence_required,
            }
        return ctx

    def _enhance_with_model(self, result: HybridResult) -> None:
        """Run semantic synthesis on pipeline output if a model is configured."""
        from .model_config import load_model_settings
        from .model_runtime import ModelRuntimeError

        settings = load_model_settings()
        profile = settings.active_profile()
        if not settings.enabled or profile is None:
            result.semantic_metadata = {"status": "disabled", "reason": "No hay modelo configurado"}
            return

        context = self._build_synthesis_context(result)
        query = context.get("ensemble", {}).get("shared_problem", "")
        if not query:
            query = context.get("pipeline_results", {}).get("final_recommendation", "")
        if not query:
            result.semantic_metadata = {"status": "skipped", "reason": "Pipeline no produjo contexto suficiente"}
            return

        # Build a synthesis prompt for the model
        synthesis_prompt = {
            "product": "CRIBA-BLACKFORGE",
            "task": (
                "Eres la capa de síntesis evolutiva de CRIBA Blackforge. "
                "Tu trabajo es analizar los resultados del pipeline de evolución de ideas "
                "y producir dos cosas:"
                "\n1. Un resumen ejecutivo (2-4 frases) que capture el hallazgo principal, "
                "el nivel de confianza y qué contradicciones o incertidumbres quedan."
                "\n2. De 1 a 3 semillas para el próximo ciclo evolutivo: preguntas o direcciones "
                "concretas que el pipeline podria explorar a continuación, basadas en lo que "
                "quedó sin resolver o en oportunidades detectadas."
                "\n\nResponde solo JSON válido. No incluyas razonamiento interno."
            ),
            "quality_rules": [
                "El resumen debe mencionar el dominio concreto del problema, no ser genérico.",
                "Cada semilla debe ser una pregunta o direccion de investigacion especifica y accionable.",
                "No inventes información que no esté en los resultados del pipeline.",
                "Usa español técnico, claro y directo.",
            ],
            "pipeline_context": context,
            "output_schema": {
                "type": "object",
                "properties": {
                    "executive_summary": {"type": "string", "minLength": 20, "maxLength": 800},
                    "next_seeds": {
                        "type": "array",
                        "minItems": 0,
                        "maxItems": 3,
                        "items": {
                            "type": "object",
                            "properties": {
                                "seed": {"type": "string", "minLength": 10, "maxLength": 300},
                                "rationale": {"type": "string", "minLength": 10, "maxLength": 300},
                            },
                            "required": ["seed", "rationale"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["executive_summary", "next_seeds"],
                "additionalProperties": False,
            },
        }

        try:
            from .model_runtime import (
                ModelRuntimeError,
                _generate_once,
                ensure_profile_available,
            )

            # Ensure the model server is running before generating
            ensure_profile_available(profile, start=True)
            profile.reasoning = "balanced"
            system = (
                "Eres la capa de síntesis evolutiva de CRIBA/BLACKFORGE. "
                "El motor determinista decide métodos, seguridad y puntuaciones; "
                "tú redactas síntesis y semillas coherentes. "
                "Devuelve exclusivamente el objeto JSON solicitado."
            )
            prompt_text = json.dumps(synthesis_prompt, ensure_ascii=False, separators=(",", ":"))
            raw = _generate_once(profile, system, prompt_text)

            # Minimal validation: try to parse top-level fields
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1] if "```" in cleaned else cleaned
                cleaned = cleaned.removeprefix("json")
            parsed = json.loads(cleaned)

            if isinstance(parsed, dict):
                summary = str(parsed.get("executive_summary", ""))
                seeds_raw = parsed.get("next_seeds", [])
                if isinstance(seeds_raw, list):
                    result.semantic_seeds = [
                        {"seed": str(s.get("seed", "")), "rationale": str(s.get("rationale", ""))}
                        for s in seeds_raw if isinstance(s, dict)
                    ]
                result.semantic_summary = summary
                result.semantic_metadata = {
                    "status": "ok",
                    "backend": profile.backend,
                    "model": profile.name,
                }
            else:
                result.semantic_metadata = {"status": "parse_error", "detail": "Respuesta no era un objeto JSON"}
        except ModelRuntimeError as exc:
            result.semantic_metadata = {"status": "model_error", "error": str(exc)}
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            result.semantic_metadata = {"status": "parse_error", "error": str(exc)}
        except Exception as exc:
            result.semantic_metadata = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

    def run(
        self,
        packet: Mapping[str, Any],
        *,
        enhance_semantics: bool = False,
    ) -> HybridResult:
        """Execute the full hybrid pipeline.

        Parameters
        ----------
        packet:
            Input packet with query, mode, constraints, etc.
        enhance_semantics:
            If True, run local LLM synthesis on the pipeline output to
            produce an executive summary and next-cycle seeds.
        """
        start = time.monotonic()
        session_id = str(uuid.uuid4())
        result = HybridResult(session_id=session_id)
        logger = self._ensure_logger(session_id)

        try:
            # ---------------------------------------------------------------
            # Phase 1: Ensemble (P3)
            # ---------------------------------------------------------------
            self._log("StageStarted", {"stage": "ensemble", "phase": 1})
            ensemble_start = time.monotonic()

            ensemble = run_ensemble(packet)
            result.ensemble = ensemble
            result.pipeline_stages_completed.append("ensemble")

            ensemble_ms = (time.monotonic() - ensemble_start) * 1000
            self._log(
                "StageCompleted",
                {
                    "stage": "ensemble",
                    "duration_ms": ensemble_ms,
                    "agreements": len(ensemble.strongest_agreements),
                    "emergent": len(ensemble.emergent_findings),
                    "disagreements": len(ensemble.substantive_disagreements),
                    "regeneration_triggered": ensemble.regeneration_triggered,
                },
            )

            # Collect generation metrics from ensemble.
            if self.enable_metrics:
                self._metrics.generation_metrics = GenerationMetrics(
                    semantic_diversity=ensemble.metrics.semantic_diversity,
                    structural_diversity=ensemble.metrics.mechanism_diversity,
                    relevance=ensemble.metrics.agreement_strength,
                    duplication_rate=0.0,
                    regeneration_rate=1.0 if ensemble.regeneration_triggered else 0.0,
                )

            # ---------------------------------------------------------------
            # Phase 2: Chain (P4) -- seeded with ensemble output
            # ---------------------------------------------------------------
            self._log("StageStarted", {"stage": "chain", "phase": 2})
            chain_start = time.monotonic()

            chain_runner = ChainRunner(storage=self.storage)
            memory = ChainMemory(original_objective=packet.get("original_query", ""))

            # Seed memory from ensemble.
            memory = self._seed_chain_memory_from_ensemble(memory, ensemble)

            chain_outputs: dict[int, Any] = {}
            for stage_num in range(1, 7):
                output, memory = chain_runner.run_stage(
                    stage_num,
                    memory,
                    packet,
                    previous_output=chain_outputs.get(stage_num - 1, {}),
                )
                chain_outputs[stage_num] = output
                self._log(
                    "ChainStageCompleted",
                    {"stage": stage_num, "type": type(output).__name__},
                    stage_id=f"stage_{stage_num}",
                )

            result.chain_outputs = chain_outputs
            result.chain_memory = memory
            result.pipeline_stages_completed.append("chain")

            chain_ms = (time.monotonic() - chain_start) * 1000
            self._log(
                "StageCompleted",
                {"stage": "chain", "duration_ms": chain_ms, "stages_completed": 6},
            )

            # Collect process metrics.
            if self.enable_metrics:
                self._metrics.process_metrics = ProcessMetrics(
                    latency_per_stage={"ensemble": ensemble_ms, "chain": chain_ms},
                    tokens_total=self.budget.tokens_spent,
                )

            # ---------------------------------------------------------------
            # Phase 3: Adversarial self-reinforcement (P5)
            # ---------------------------------------------------------------
            stage6 = chain_outputs.get(6)
            if stage6 and isinstance(stage6, Stage6Output) and stage6.winning_proposal:
                self._log("StageStarted", {"stage": "adversarial", "phase": 3})
                adv_start = time.monotonic()

                adversarial_runner = AdversarialSelfReinforcement()
                adv_packet = self._build_adversarial_packet(stage6, ensemble)

                thesis, adversarial, resolution = adversarial_runner.run(
                    adv_packet,
                    is_blackforge=(packet.get("mode") == "blackforge"),
                )

                result.thesis = thesis
                result.adversarial = adversarial
                result.resolution = resolution
                result.pipeline_stages_completed.append("adversarial")

                adv_ms = (time.monotonic() - adv_start) * 1000
                self._log(
                    "StageCompleted",
                    {
                        "stage": "adversarial",
                        "duration_ms": adv_ms,
                        "verdict": resolution.final_status,
                        "survived_challenges": len(resolution.survived_challenges),
                        "failed_challenges": len(resolution.failed_challenges),
                    },
                )

                # Collect result metrics.
                if self.enable_metrics:
                    self._metrics.result_metrics = ResultMetrics(
                        ideas_validated=1 if resolution.final_status in ("survives", "survives_with_conditions") else 0,
                        human_acceptance=1.0 if resolution.final_status == "survives" else 0.5,
                    )

            # ---------------------------------------------------------------
            # Final recommendation
            # ---------------------------------------------------------------
            if result.resolution:
                if result.resolution.final_status in ("survives", "survives_with_conditions"):
                    result.final_recommendation = stage6.winning_proposal if isinstance(stage6, Stage6Output) else ""
                    result.final_confidence = "confirmed"
                elif result.resolution.final_status == "rejected":
                    result.final_recommendation = "Tesis rechazada; revisar hipotesis"
                    result.final_confidence = "rejected"
                else:
                    result.final_recommendation = f"Requiere experimento: {result.resolution.evidence_required}"
                    result.final_confidence = "hypothesis"
            elif isinstance(stage6, Stage6Output):
                result.final_recommendation = stage6.winning_proposal
                result.final_confidence = "hypothesis"

            total_ms = (time.monotonic() - start) * 1000
            result.total_duration_ms = total_ms

            self._log(
                "PipelineCompleted",
                {
                    "stages": result.pipeline_stages_completed,
                    "duration_ms": total_ms,
                    "final_confidence": result.final_confidence,
                },
            )

        except Exception as e:
            result.error = str(e)
            result.total_duration_ms = (time.monotonic() - start) * 1000
            self._log(
                "PipelineError",
                {"error": str(e), "stages_completed": result.pipeline_stages_completed},
                category=EventCategory.OPERATIONAL,
                severity="error",
            )

        # ---------------------------------------------------------------
        # Phase 4: Semantic enhancement (optional, after pipeline)
        # ---------------------------------------------------------------
        if enhance_semantics and result.error is None:
            self._log("StageStarted", {"stage": "semantic_synthesis", "phase": 4})
            semantic_start = time.monotonic()
            self._enhance_with_model(result)
            semantic_ms = (time.monotonic() - semantic_start) * 1000
            self._log(
                "StageCompleted",
                {
                    "stage": "semantic_synthesis",
                    "duration_ms": semantic_ms,
                    "status": result.semantic_metadata.get("status", "unknown"),
                },
            )

        return result


def run_hybrid(packet: Mapping[str, Any], **kwargs: Any) -> HybridResult:
    """Convenience function to run the full hybrid pipeline.

    Parameters
    ----------
    packet:
        Input packet with query, mode, constraints, etc.
    enhance_semantics:
        If True, run local LLM synthesis on the pipeline output.
    """
    enhance_semantics = kwargs.pop("enhance_semantics", False)
    orchestrator = HybridOrchestrator(**kwargs)
    return orchestrator.run(packet, enhance_semantics=enhance_semantics)
