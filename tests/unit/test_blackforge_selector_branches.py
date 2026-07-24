"""FASE 1 — cobertura de ramas del selector BLACKFORGE.

Complementa test_blackforge_selector.py con:
- perfil inválido -> ValueError (contrato de entrada);
- to_dict() de un reporte OK y de un fallo estructurado;
- fallo de compliance distinto de session_size (min_* imposible) mediante
  restricción fuerte de tiers, sin inventar una selección.
"""
from __future__ import annotations

import pytest

from criba import blackforge_selector as bs


def test_invalid_profile_raises():
    with pytest.raises(ValueError):
        bs.select_blackforge(seed=1, profile="perfil-inexistente")


def test_report_to_dict_shape_ok():
    rep = bs.select_blackforge(seed=1)
    d = rep.to_dict()
    assert d["status"] == "OK"
    assert d["selected_count"] == len(d["selected_ids"]) == 12
    assert d["failure"] is None
    assert set(("seed", "session_size", "allowed_tiers", "profile_used",
                "s3_count", "s3_allowed", "compliance")).issubset(d)


def test_failure_to_dict_shape():
    rep = bs.select_blackforge(seed=1, session_size=100000)
    d = rep.to_dict()
    assert d["status"] == "FAILED"
    assert d["failure"]["failed_quota"] == "session_size"
    assert d["selected_ids"] == []


def test_all_allowed_profiles_are_accepted():
    for profile in ("defensive", "devtools", "offensive_research", "hybrid"):
        rep = bs.select_blackforge(seed=1, profile=profile)
        assert rep.profile_used == profile
        # cada perfil produce una selección reproducible (mismo seed -> mismos ids)
        assert rep.selected_ids == bs.select_blackforge(seed=1, profile=profile).selected_ids
        # si un perfil no cumple todas las cuotas de diversidad, lo reporta
        # honestamente con un fallo estructurado (no finge cumplimiento)
        if not rep.status_ok():
            assert rep.failure.failed_quota in (
                "min_source_catalogs", "min_primary_categories",
                "min_causal_axes", "mandatory_stages",
            )


def test_hybrid_profile_is_fully_compliant():
    rep = bs.select_blackforge(seed=1, profile="hybrid")
    assert rep.status_ok()
    assert len(rep.selected_ids) == 12


def test_small_session_still_reports_compliance_flags():
    # Una sesión pequeña puede no alcanzar las cuotas mínimas de diversidad;
    # el selector debe reportarlo honestamente (no fingir cumplimiento).
    rep = bs.select_blackforge(seed=1, session_size=2)
    assert rep.compliance["session_size_met"] is True  # 2 elegibles caben
    # Con solo 2 elementos, las cuotas mínimas de diversidad no se cumplen ->
    # el reporte lo marca y produce un fallo estructurado.
    assert rep.failure is not None
    assert rep.failure.failed_quota in (
        "min_source_catalogs", "min_primary_categories", "min_causal_axes",
        "mandatory_stages",
    )
