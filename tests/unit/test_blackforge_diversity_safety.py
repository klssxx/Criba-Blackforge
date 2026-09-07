"""DV10 (megaprompt §38/§63): la diversidad de BLACKFORGE nunca debilita
los safety gates. Con el selector REAL (catálogo inyectado vía monkeypatch
de _load_catalog): un candidato S3_HIGH_CONTROL con score y diversidad
máximos no entra sin la triada de aprobación, aunque hayan seguros con
menor diversidad que ocupen las plazas.
"""
from __future__ import annotations

import pytest

import criba.blackforge_selector as bfs
from criba.blackforge_selector import select_blackforge


def _catalog_record(blackforge_id: str, *, safety_class: str, tier: str,
                    profile_score: float, diversity: float, catalog: str,
                    fcat: str, axis: str, stage: str) -> dict:
    return {
        "blackforge_id": blackforge_id,
        "id": blackforge_id,
        "name": blackforge_id,
        "activation_tier": tier,
        "safety_class": safety_class,
        "profile_hybrid": profile_score,
        "diversity_contribution_v2": diversity,
        "selection_weight": 1,
        "source_family": family_of(blackforge_id),
        "source_catalog": catalog,
        "functional_category_primary": fcat,
        "causal_axis_primary": axis,
        "pipeline_stage": stage,
    }


def family_of(blackforge_id: str) -> str:
    return f"fam-{blackforge_id}"


def _catalog() -> tuple[dict, list[dict]]:
    meta = {
        "selection_policy": {
            "constraints": {
                "maximum_per_primary_category": 3,
                "maximum_per_source_family": 2,
                "maximum_unknown_causal_axis": 2,
                "minimum_source_catalogs": 3,
                "minimum_primary_categories": 5,
                "minimum_causal_axes": 4,
            },
            "allowed_tiers_default": ["essential", "core"],
        }
    }
    recs = [
        # S3 con score y diversidad MÁXIMOS: solo entra con la triada completa.
        _catalog_record("BF-S3-DIVERSO", safety_class="S3_HIGH_CONTROL",
                        tier="essential", profile_score=99, diversity=1.0,
                        catalog="catA", fcat="recon", axis="quien_decide",
                        stage="ROMPER"),
        # 5 seguros con cobertura completa de cuotas (5 categorías, 4 ejes,
        # 3 catálogos, 4 estadios) y menor diversidad que el S3.
        _catalog_record("BF-S1-A", safety_class="S1", tier="essential",
                        profile_score=70, diversity=0.4, catalog="catA",
                        fcat="deteccion", axis="si_falla", stage="DIVERGIR"),
        _catalog_record("BF-S1-B", safety_class="S1", tier="core",
                        profile_score=68, diversity=0.5, catalog="catB",
                        fcat="resiliencia", axis="cuando", stage="ATACAR"),
        _catalog_record("BF-S1-C", safety_class="S1", tier="core",
                        profile_score=66, diversity=0.6, catalog="catC",
                        fcat="control", axis="evidencia", stage="EVALUAR"),
        _catalog_record("BF-S1-D", safety_class="S1", tier="core",
                        profile_score=64, diversity=0.7, catalog="catD",
                        fcat="humanos", axis="quien_decide", stage="ROMPER"),
        _catalog_record("BF-S1-E", safety_class="S1", tier="core",
                        profile_score=62, diversity=0.8, catalog="catE",
                        fcat="respuesta", axis="si_falla", stage="DIVERGIR"),
    ]
    return meta, recs


def test_dv10_diversity_never_bypasses_safety_gates(monkeypatch) -> None:
    monkeypatch.setattr(bfs, "_load_catalog", _catalog)
    report = select_blackforge(seed=1, session_size=5, profile="hybrid")
    assert report.status_ok(), report.failure
    ids = set(report.selected_ids)
    assert "BF-S3-DIVERSO" not in ids, (
        "un candidato S3 no puede entrar por máxima diversidad sin triada de aprobación"
    )
    assert report.s3_count == 0
    assert len(ids) == 5


def test_dv10b_s3_only_with_full_approval_triad(monkeypatch) -> None:
    """Con la triada completa de autorización, S3 puede entrar (cap 1)."""
    monkeypatch.setattr(bfs, "_load_catalog", _catalog)
    report = select_blackforge(
        seed=1, session_size=5, profile="hybrid",
        explicit_high_control_approval=True,
        authorized_scope_confirmed=True,
        sandbox_available=True,
    )
    assert report.status_ok(), report.failure
    assert report.selected_ids.count("BF-S3-DIVERSO") == 1
    assert report.s3_count == 1
