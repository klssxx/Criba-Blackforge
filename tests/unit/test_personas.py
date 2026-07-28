"""Contract tests for the P2 personas layer (HIPERMEGAPROMPT §1)."""
from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from criba import constants
from criba.constraints import FindingConfidence
from criba.engine import activate
from criba.personas import (
    PERSONAS_SCHEMA_VERSION,
    DEFAULT_TEAM_PROTOCOL,
    CompositePersonaDimensions,
    MinorityReport,
    PersonaA,
    PersonaB,
    PersonaC,
    PersonaD,
    PersonaDiversityReport,
    PersonaResult,
    TeamProtocol,
    build_persona_prompt,
    evaluate_persona_diversity,
    run_persona,
    run_personas,
    validate_team_protocol,
)


def _packet() -> dict[str, object]:
    return {
        "original_query": "Reducir fraude en pagos sin elevar la fricción.",
        "intent": "INNOVAR",
        "model_instruction": "Usa únicamente el paquete para proponer mecanismos.",
        "supporting_methods": [
            {"id": "M01", "name": "Análisis de incentivos", "reason": "explica el abuso"},
        ],
        "innovation": {
            "known_space": ["reglas estáticas", "verificación manual"],
            "assumptions": ["más control implica más fricción"],
            "ruptures": [{"operation": "invertir", "result": "evaluar señales antes del pago"}],
        },
        "protected_assets": ["cuentas de pago"],
        "threat_actors": ["defraudador externo"],
        "authorization_state": "pending",
    }


class _JsonBackend:
    def __init__(self, response: dict[str, object]) -> None:
        self._response = response

    def is_available(self) -> bool:
        return True

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        assert "PERSONA A" in prompt
        assert "solo JSON" in system_prompt
        return json.dumps(self._response)


class _InvalidBackend:
    def is_available(self) -> bool:
        return True

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return "not-json"


class TestPersonaContracts:
    def test_schema_version_is_frozen(self) -> None:
        assert PERSONAS_SCHEMA_VERSION == "1.0.0"
        assert PersonaResult.model_fields["schema_version"].default == "1.0.0"

    @pytest.mark.parametrize(
        ("model", "expected_fields"),
        [
            (PersonaA, {"current_structure", "structural_problem", "root_component", "proposed_change", "shared_or_specialized", "affected_modules", "interfaces", "state_changes", "persistence_changes", "migration", "failure_modes", "simpler_alternative", "evidence_required", "recommendation"}),
            (PersonaB, {"known_space", "dominant_paradigms", "shared_assumptions", "unresolved_gaps", "operators_selected", "structural_directions", "mechanism_diversity", "novelty_status", "technical_translation", "strongest_direction", "strongest_counterargument", "validation_needed"}),
            (PersonaC, {"confirmed_facts", "inferred_claims", "unsupported_claims", "evidence_quality", "conflicting_evidence", "confidence", "falsification_tests", "pass_fail_criteria", "reproducibility", "traceability_gaps", "risk_of_wrong_decision", "recommendation"}),
            (PersonaD, {"assets", "threat_actors", "attack_surfaces", "trust_boundaries", "attack_hypotheses", "existing_controls", "likely_bypasses", "detection", "containment", "recovery", "evidence_status", "authorization_status", "residual_risk", "recommendation"}),
        ],
    )
    def test_each_contract_exposes_its_approved_schema(
        self, model: type[PersonaA | PersonaB | PersonaC | PersonaD], expected_fields: set[str]
    ) -> None:
        assert set(model.model_fields) == expected_fields

    def test_contracts_reject_missing_or_unknown_fields(self) -> None:
        with pytest.raises(ValidationError):
            PersonaA(current_structure="only one field")

        result = run_persona("A", _packet())
        with pytest.raises(ValidationError):
            PersonaA(**(result.output.model_dump() | {"unapproved": "field"}))

    def test_evidence_auditor_cannot_claim_confirmation_without_facts(self) -> None:
        result = run_persona("C", _packet())
        payload = result.output.model_dump() | {
            "confirmed_facts": [],
            "confidence": FindingConfidence.CONFIRMED,
        }
        with pytest.raises(ValidationError, match="confirmed_facts"):
            PersonaC(**payload)

    def test_composite_persona_integrates_all_three_dimensions(self) -> None:
        dimensions = CompositePersonaDimensions()
        assert dimensions.value_and_incentives
        assert dimensions.human_and_organizational_behavior
        assert dimensions.evidence_probability_and_risk


class TestTeamProtocol:
    def test_protocol_is_independent_and_requires_minority_report(self) -> None:
        protocol = TeamProtocol()
        assert protocol == DEFAULT_TEAM_PROTOCOL
        assert protocol.independent_first_pass
        assert protocol.separate_analysis
        assert protocol.minority_report_required

    def test_protocol_cannot_be_weakened(self) -> None:
        with pytest.raises(ValidationError):
            TeamProtocol(independent_first_pass=False)


class TestPromptAndExecution:
    def test_prompt_reuses_engine_and_llm_material_with_persona_contract(self) -> None:
        prompt = build_persona_prompt("B", _packet())
        assert "# Consulta original" in prompt
        assert "# MANDATORY_MODEL_PACKET" in prompt
        assert "MÉTODOS DISPONIBLES" in prompt
        assert "PERSONA B" in prompt
        assert "innovation_architect_output" in prompt

    def test_prompt_excludes_prior_persona_output_to_preserve_isolation(self) -> None:
        packet = _packet() | {"prior_persona_outputs": [{"secret": "do not expose"}]}
        prompt = build_persona_prompt("A", packet)
        assert "do not expose" not in prompt

    def test_none_backend_has_explicit_deterministic_provenance(self) -> None:
        result = run_persona("A", _packet())
        assert result.persona_id == "A"
        assert result.source == "deterministic_fallback"
        assert result.confidence == "inferred"
        assert isinstance(result.output, PersonaA)

    def test_valid_backend_response_is_parsed_against_the_right_contract(self) -> None:
        fallback = run_persona("A", _packet()).output
        backend = _JsonBackend(fallback.model_dump())
        result = run_persona("A", _packet(), backend=backend)
        assert result.source == "llm"
        assert result.confidence == "unverified"
        assert isinstance(result.output, PersonaA)

    def test_invalid_backend_response_falls_back_without_claiming_evidence(self) -> None:
        result = run_persona("C", _packet(), backend=_InvalidBackend())
        assert result.source == "deterministic_fallback"
        assert result.confidence == "inferred"
        assert result.fallback_reason == "invalid_backend_output"
        assert isinstance(result.output, PersonaC)

    def test_all_four_personas_are_contract_distinct_and_round_trip(self) -> None:
        results = run_personas(_packet())
        assert [result.persona_id for result in results] == ["A", "B", "C", "D"]
        assert [type(result.output) for result in results] == [PersonaA, PersonaB, PersonaC, PersonaD]
        for result in results:
            restored = PersonaResult.model_validate_json(result.model_dump_json())
            assert restored == result

    def test_persona_layer_is_additive_and_does_not_migrate_or_mutate_the_packet(self) -> None:
        packet = _packet()
        before = json.loads(json.dumps(packet))
        results = run_personas(packet)
        assert packet == before
        assert {result.packet_fingerprint for result in results}
        assert len({result.packet_fingerprint for result in results}) == 1
        assert len({result.prompt_fingerprint for result in results}) == 4

    def test_result_rejects_an_unfrozen_schema_version(self) -> None:
        result = run_persona("A", _packet())
        with pytest.raises(ValidationError):
            PersonaResult(**(result.model_dump() | {"schema_version": "0.9.0"}))

    def test_engine_feature_flag_is_off_by_default(self) -> None:
        assert constants.FEATURES["compound_personas"] is False
        packet = activate("Reducir fraude en pagos sin elevar la fricción.")
        assert "persona_analysis" not in packet

    def test_engine_feature_flag_adds_isolated_p2_results(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(constants.FEATURES, "compound_personas", True)
        packet = activate("Reducir fraude en pagos sin elevar la fricción.")
        analysis = packet["persona_analysis"]

        assert analysis["status"] == "AWAITING_P3_SYNTHESIS"
        assert analysis["diversity"]["is_diverse"] is True
        assert analysis["protocol_validation"]["requires_minority_report"] is True
        assert [item["persona_id"] for item in analysis["results"]] == ["A", "B", "C", "D"]


class TestDifferentiationAndMinorityReport:
    def test_distinct_personas_pass_diversity_check(self) -> None:
        report = evaluate_persona_diversity(run_personas(_packet()))
        assert isinstance(report, PersonaDiversityReport)
        assert report.is_diverse
        assert report.reason == "distinct_persona_contributions"

    def test_repeated_semantic_contribution_is_rejected(self) -> None:
        results = run_personas(_packet())
        clones = []
        for result in results:
            payload = result.output.model_dump()
            for key, value in payload.items():
                if isinstance(value, list):
                    payload[key] = ["misma contribución"]
                elif key == "confidence":
                    payload[key] = FindingConfidence.HYPOTHESIS
                elif key == "authorization_status":
                    payload[key] = "pending"
                else:
                    payload[key] = "misma contribución"
            clones.append(result.model_copy(update={"output": type(result.output)(**payload)}))

        report = evaluate_persona_diversity(clones)
        assert not report.is_diverse
        assert report.reason == "identical_semantic_contributions"

    def test_disagreement_requires_a_minority_report(self) -> None:
        results = run_personas(_packet())
        missing = validate_team_protocol(results)
        assert not missing.is_valid
        assert missing.requires_minority_report

        report = MinorityReport(
            dissenting_persona_ids=["D"],
            disagreement="La exposición operativa no está suficientemente demostrada.",
            evidence_needed=["Prueba segura en entorno autorizado"],
            impact_on_recommendation="No desplegar hasta validar el control.",
        )
        accepted = validate_team_protocol(results, minority_report=report)
        assert accepted.is_valid
        assert accepted.requires_minority_report
