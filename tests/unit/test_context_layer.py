"""Tests for context_layer.py — HIPERMEGAPROMPT §2."""
from __future__ import annotations

import pytest
from criba.context_layer import (
    InnovationContext,
    BlackforgeContext,
    OperatingMode,
    ContextIntegrityStatus,
    detect_domain,
    build_context,
    extend_for_blackforge,
    validate_context_integrity,
)


# ---------------------------------------------------------------------------
# detect_domain
# ---------------------------------------------------------------------------

class TestDetectDomain:
    def test_seguridad(self) -> None:
        assert detect_domain("Proteger el sistema contra ataques") == "seguridad"

    def test_negocio(self) -> None:
        assert detect_domain("Reducir el churn de clientes") == "negocio"

    def test_tecnologia(self) -> None:
        assert detect_domain("Mejorar la arquitectura del API") == "tecnologia"

    def test_ia(self) -> None:
        assert detect_domain("Entrenar un modelo de machine learning") == "ia"

    def test_general_fallback(self) -> None:
        assert detect_domain("xyzzy plugh") == "general"

    def test_12_domains_covered(self) -> None:
        queries = [
            ("seguridad", "ataque al sistema"),
            ("negocio", "ventas de la empresa"),
            ("tecnologia", "codigo software"),
            ("ia", "inteligencia artificial"),
            ("gobernanza", "gobernanza dao"),
            ("etica", "etica sesgo"),
            ("salud", "paciente hospital"),
            ("educacion", "estudiante escuela"),
            ("transporte", "vehiculo logistica"),
            ("energia", "energia edificio"),
            ("alimentos", "cadena de alimentos desperdicio"),
            ("recursos_humanos", "turno jornada"),
        ]
        for expected, q in queries:
            assert detect_domain(q) == expected, f"Failed for {q}"


# ---------------------------------------------------------------------------
# InnovationContext
# ---------------------------------------------------------------------------

class TestInnovationContext:
    def test_defaults(self) -> None:
        ctx = InnovationContext(original_query="test query")
        assert ctx.mode == OperatingMode.CRIBA
        assert ctx.original_query == "test query"
        assert ctx.context_id  # auto-generated
        assert ctx.created_at  # auto-generated

    def test_normalized_query_auto_fill(self) -> None:
        ctx = InnovationContext(original_query="  Hola Mundo  ")
        assert ctx.normalized_query == "hola mundo"

    def test_normalized_query_preserved_if_set(self) -> None:
        ctx = InnovationContext(original_query="test", normalized_query="custom")
        assert ctx.normalized_query == "custom"

    def test_serialization_roundtrip(self) -> None:
        ctx = InnovationContext(original_query="test", primary_domain="seguridad")
        data = ctx.model_dump()
        restored = InnovationContext(**data)
        assert restored.original_query == ctx.original_query
        assert restored.primary_domain == "seguridad"


# ---------------------------------------------------------------------------
# BlackforgeContext
# ---------------------------------------------------------------------------

class TestBlackforgeContext:
    def test_extends_innovation(self) -> None:
        ctx = BlackforgeContext(original_query="test")
        assert ctx.mode == OperatingMode.BLACKFORGE
        assert ctx.protected_assets == []
        assert ctx.threat_actors == []

    def test_full_blackforge_fields(self) -> None:
        ctx = BlackforgeContext(
            original_query="test",
            protected_assets=["API keys", "user data"],
            threat_actors=["external attacker"],
            attack_surfaces=["web interface"],
            trust_boundaries=["API gateway"],
            authorization_scope="internal lab",
            authorized_environment=True,
        )
        assert ctx.protected_assets == ["API keys", "user data"]
        assert ctx.authorized_environment is True

    def test_serialization_roundtrip(self) -> None:
        ctx = BlackforgeContext(
            original_query="pentest API",
            protected_assets=["tokens"],
            authorization_scope="lab",
        )
        data = ctx.model_dump()
        restored = BlackforgeContext(**data)
        assert restored.protected_assets == ["tokens"]
        assert restored.authorization_scope == "lab"


# ---------------------------------------------------------------------------
# extend_for_blackforge
# ---------------------------------------------------------------------------

class TestExtendForBlackforge:
    def test_preserves_base_fields(self) -> None:
        ctx = InnovationContext(
            original_query="test",
            primary_domain="seguridad",
            actors=["attacker"],
        )
        bf = extend_for_blackforge(ctx)
        assert bf.mode == OperatingMode.BLACKFORGE
        assert bf.original_query == "test"
        assert bf.primary_domain == "seguridad"
        assert bf.actors == ["attacker"]

    def test_adds_empty_blackforge_fields(self) -> None:
        ctx = InnovationContext(original_query="test")
        bf = extend_for_blackforge(ctx)
        assert bf.protected_assets == []
        assert bf.threat_actors == []
        assert bf.authorization_scope == ""


# ---------------------------------------------------------------------------
# validate_context_integrity
# ---------------------------------------------------------------------------

class TestContextIntegrity:
    def test_complete_context(self) -> None:
        ctx = InnovationContext(
            original_query="test",
            central_problem="problem",
            primary_domain="tecnologia",
            actors=["users"],
            known_solutions=["solution A"],
            assumptions=["assumption 1"],
        )
        report = validate_context_integrity(ctx)
        assert report.status == ContextIntegrityStatus.COMPLETE
        assert "original_query" in report.confirmed_data
        assert "primary_domain" in report.confirmed_data

    def test_incomplete_context(self) -> None:
        ctx = InnovationContext(original_query="")
        report = validate_context_integrity(ctx)
        assert report.status == ContextIntegrityStatus.INCOMPLETE
        assert "original_query" in report.missing_information

    def test_partial_context(self) -> None:
        ctx = InnovationContext(
            original_query="test",
            known_solutions=[],
        )
        report = validate_context_integrity(ctx)
        assert report.status == ContextIntegrityStatus.PARTIAL

    def test_prohibited_inferences_always_present(self) -> None:
        ctx = InnovationContext(original_query="test")
        report = validate_context_integrity(ctx)
        assert len(report.prohibited_inferences) == 3


# ---------------------------------------------------------------------------
# build_context
# ---------------------------------------------------------------------------

class TestBuildContext:
    def test_basic_build(self) -> None:
        ctx = build_context("Mejorar la seguridad del API")
        assert ctx.original_query == "Mejorar la seguridad del API"
        assert ctx.primary_domain == "seguridad"
        assert ctx.normalized_query == "mejorar la seguridad del api"
        assert ctx.actors  # should detect actors
        assert ctx.assumptions  # should have domain assumptions

    def test_with_engine_output(self) -> None:
        carto = {
            "known_space": ["WAF exists", "IDS exists"],
            "ruptures": [{"operation": "invert", "result": "invert assumption"}],
            "actors": ["attacker"],
            "assets": ["data"],
            "constraints": ["budget"],
        }
        ctx = build_context("test", engine_output=carto)
        assert ctx.known_solutions == ["WAF exists", "IDS exists"]
        assert ctx.actors == ["attacker"]
        assert ctx.constraints == ["budget"]

    def test_desired_outcome_inference(self) -> None:
        ctx1 = build_context("Innovar en el mercado")
        assert "alternativas" in ctx1.desired_outcome.lower() or "innov" in ctx1.desired_outcome.lower()

        ctx2 = build_context("Analizar los resultados")
        assert "análisis" in ctx2.desired_outcome.lower()

    def test_unknowns_populated(self) -> None:
        carto = {"unknowns": ["unknown_a", "unknown_b"]}
        ctx = build_context("test", engine_output=carto)
        assert "unknown_a" in ctx.unknowns
