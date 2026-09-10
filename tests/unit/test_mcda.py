"""DOMAIN 11 — MCDA: fórmula canónica única de oportunidad.

Honestidad ante todo: UNKNOWN ≠ 0; el composite expone su cobertura;
los pesos son explícitos y validados; determinista; ordena exploración,
nunca afirma calidad absoluta.
"""
from __future__ import annotations

import pytest

from criba.mcda import DIMENSIONS, Coverage, MCDAResult, score, validate_weights

FULL_INPUTS: dict[str, float | None] = {
    "novelty": 0.8, "evidence": 0.5, "confidence": 0.6, "feasibility": 0.7,
    "growth": 0.4, "underhype": 0.9, "trl": 0.3, "prototypeability": 0.8,
    "competition": 0.6, "patent_risk": 0.7, "opportunity": 0.5,
}


def test_weights_canonicos_suman_uno() -> None:
    default = {name: weight for name, weight in DIMENSIONS}
    validate_weights(default)  # no lanza
    assert len(DIMENSIONS) == 11, "DOMAIN 11 declara 11 dimensiones"
    names = {name for name, _ in DIMENSIONS}
    assert {"novelty", "evidence", "confidence", "feasibility", "growth",
            "underhype", "trl", "prototypeability", "competition",
            "patent_risk", "opportunity"} == names


def test_full_inputs_producen_full_coverage_y_composite_estable() -> None:
    a = score(FULL_INPUTS)
    b = score(dict(FULL_INPUTS))
    assert a.coverage is Coverage.FULL
    assert a.present_count == 11
    assert a.composite == b.composite  # determinista
    assert 0.0 <= a.composite <= 1.0


def test_unknown_no_es_cero() -> None:
    """Falsador central: una dimensión ausente NO es una dimensión de 0.0."""
    partial = dict(FULL_INPUTS)
    partial["novelty"] = None
    partial["evidence"] = None
    result = score(partial)
    assert result.coverage is Coverage.PARTIAL
    assert set(result.unknown_dimensions) == {"novelty", "evidence"}
    novelty_dim = next(d for d in result.dimensions if d.name == "novelty")
    assert not novelty_dim.present
    assert novelty_dim.to_dict()["value"] is None  # no 0.0


def test_zero_si_cuenta_como_presente() -> None:
    """Un 0.0 medido es evidencia (a diferencia del None): cambia el composite."""
    with_zero = dict(FULL_INPUTS, novelty=0.0)
    without = dict(FULL_INPUTS, novelty=None)
    assert score(with_zero).composite != score(without).composite


def test_weak_coverage_no_es_comparable() -> None:
    sparse = {k: v for k, v in FULL_INPUTS.items() if k in ("novelty", "evidence")}
    result = score(sparse)
    assert result.coverage is Coverage.WEAK
    assert result.present_count == 2
    assert result.composite > 0.0  # computa con las presentes…


def test_falsador_fuera_de_rango_no_se_silencia() -> None:
    with pytest.raises(ValueError, match="novelty"):
        score(dict(FULL_INPUTS, novelty=1.5))
    with pytest.raises(ValueError, match="evidence"):
        score(dict(FULL_INPUTS, evidence=-0.1))
    with pytest.raises(ValueError, match="no numérico"):
        score(dict(FULL_INPUTS, trl="alto"))  # type: ignore[dict-item]
    # bool es int en Python: prohibido colapsar True/False con 1.0/0.0
    with pytest.raises(ValueError, match="no numérico"):
        score(dict(FULL_INPUTS, confidence=True))  # type: ignore[dict-item]


def test_pesos_invalidos_rechazados() -> None:
    bad_sum = {name: 0.1 for name, _ in DIMENSIONS}  # suma 1.1
    with pytest.raises(ValueError, match="sumar 1.0"):
        score(FULL_INPUTS, weights=bad_sum)
    with pytest.raises(ValueError, match="pesos ausentes"):
        validate_weights({"novelty": 1.0})
    with pytest.raises(ValueError, match="desconocidas"):
        validate_weights({name: 1.0 / 11 for name, _ in DIMENSIONS} | {"madeup": 0.0})


def test_pesos_personalizados_cambian_el_composite_sin_romper_contrato() -> None:
    """Redistribución explícita (novelty gana peso; decayed pierde): suma 1.0
    validada y composite distinto — los pesos son decisión declarada."""
    base = score(FULL_INPUTS)
    heavy_novelty = {
        "novelty": 0.50, "evidence": 0.06, "confidence": 0.04, "feasibility": 0.14,
        "growth": 0.03, "underhype": 0.03, "trl": 0.06, "prototypeability": 0.04,
        "competition": 0.04, "patent_risk": 0.04, "opportunity": 0.02,
    }
    assert abs(sum(heavy_novelty.values()) - 1.0) < 1e-9
    weighted = score(FULL_INPUTS, weights=heavy_novelty)
    assert weighted.coverage is Coverage.FULL
    assert weighted.composite != base.composite
    # novelty domina: subir su peso sobre un valor alto sube el composite
    assert weighted.composite > base.composite


def test_fuentes_viajan_para_procedencia() -> None:
    result = score(FULL_INPUTS, sources={"novelty": "T081:local_novelty",
                                         "trl": "T102:estimation"})
    trl = next(d for d in result.dimensions if d.name == "trl")
    assert trl.source == "T102:estimation"
    assert trl.to_dict()["source"] == "T102:estimation"
    with pytest.raises(ValueError, match="desconocidas"):
        score(FULL_INPUTS, sources={"inventada": "x"})


def test_to_dict_es_serializable_y_no_fabrica_valores() -> None:
    partial = dict(FULL_INPUTS, growth=None)
    as_dict = score(partial).to_dict()
    growth = next(d for d in as_dict["dimensions"] if d["name"] == "growth")
    assert growth["value"] is None and growth["present"] is False
    assert isinstance(as_dict["composite"], float)


def test_orden_exploracion_por_composite() -> None:
    """Uso previsto: ordenar candidatos para explorar, no proclamar calidad."""
    a = score({**FULL_INPUTS, "novelty": 0.9})
    b = score({**FULL_INPUTS, "novelty": 0.2})
    assert a.composite > b.composite


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
