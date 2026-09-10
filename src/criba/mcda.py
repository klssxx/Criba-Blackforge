"""DOMAIN 11 — SCORING: fórmula canónica única de oportunidad (MCDA).

Blueprint §DOMAIN 11: la fórmula final debe vivir en UN solo módulo canónico,
responsable de 11 dimensiones: novelty, evidence, confidence, feasibility,
growth, underhype, TRL, prototypeability, competition, patent risk, opportunity.

Reglas de honestidad (mismas del resto del sistema):
- Entradas ausentes ⇒ dimensión UNKNOWN (no 0.0): la ausencia de evidencia no
  es evidencia de ausencia. Cada dimensión reporta presente/ausente.
- El composite solo computa con presentes; el resultado expone cuántas
  dimensiones sustentan el número y un estado COVERAGE (FULL/PARTIAL/WEAK).
- Pesos declarados, sumando 1.0; validados al construir (sin pesos tácitos).
- Determinista: nada de aleatoriedad ni llamadas a modelos.
- Determina ORDEN de exploración; nunca afirma calidad absoluta (§CRIBA:
  la evidencia desmiente, el score no).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Las 11 dimensiones canónicas del DOMAIN 11, con peso por defecto y origen
# de evidencia. Peso = relevancia relativa explícita; validado suma ≈ 1.
DIMENSIONS: tuple[tuple[str, float], ...] = (
    ("novelty", 0.16),
    ("evidence", 0.14),
    ("confidence", 0.10),
    ("feasibility", 0.12),
    ("growth", 0.08),
    ("underhype", 0.08),
    ("trl", 0.10),
    ("prototypeability", 0.08),
    ("competition", 0.06),
    ("patent_risk", 0.06),
    ("opportunity", 0.02),
)


class Coverage(str, Enum):
    FULL = "FULL"          # 11/11 dimensiones presentes
    PARTIAL = "PARTIAL"    # ≥7 presentes
    WEAK = "WEAK"          # <7 presentes: el composite no es comparable


@dataclass(frozen=True)
class DimensionValue:
    name: str
    value: float          # 0.0–1.0
    present: bool
    source: str = ""      # de dónde salió (técnica/campo/clase)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "value": round(self.value, 6) if self.present else None,
                "present": self.present, "source": self.source}


@dataclass(frozen=True)
class MCDAResult:
    composite: float
    coverage: Coverage
    present_count: int
    dimensions: tuple[DimensionValue, ...]
    unknown_dimensions: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "composite": round(self.composite, 6),
            "coverage": self.coverage.value,
            "present_count": self.present_count,
            "dimensions": [d.to_dict() for d in self.dimensions],
            "unknown_dimensions": list(self.unknown_dimensions),
        }


def validate_weights(weights: dict[str, float]) -> None:
    """Pesos explícitos: cubren las 11 dims y suman ≈1 (tolerancia 1e-9)."""
    names = {name for name, _ in DIMENSIONS}
    missing = names - set(weights)
    if missing:
        raise ValueError(f"pesos ausentes para: {sorted(missing)}")
    extra = set(weights) - names
    if extra:
        raise ValueError(f"pesos de dimensiones desconocidas: {sorted(extra)}")
    total = sum(weights.values())
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"los pesos deben sumar 1.0 (suma={total})")


def score(
    inputs: dict[str, float | None],
    *,
    weights: dict[str, float] | None = None,
    sources: dict[str, str] | None = None,
) -> MCDAResult:
    """Composite MCDA determinista sobre entradas 0.0–1.0 (o None=UNKNOWN).

    - Valor fuera de [0,1] → ValueError (sin clamps silenciosos).
    - None/ausente ⇒ dimensión UNKNOWN: excluida del composite y reportada.
    - composite = Σ(w_i·v_i) sobre presentes, renormalizado por su peso total
      (el número es comparable SOLO entre resultados de igual coverage).
    """
    w = dict(weights) if weights else {name: weight for name, weight in DIMENSIONS}
    validate_weights(w)
    if sources is not None:
        unknown_sources = set(sources) - {name for name, _ in DIMENSIONS}
        if unknown_sources:
            raise ValueError(f"fuentes de dimensiones desconocidas: {sorted(unknown_sources)}")

    dimensions: list[DimensionValue] = []
    weighted_sum = 0.0
    weight_total = 0.0
    for name, _ in DIMENSIONS:
        raw = inputs.get(name)
        if raw is None:
            dimensions.append(DimensionValue(name=name, value=0.0, present=False,
                                             source=(sources or {}).get(name, "")))
            continue
        if not isinstance(raw, (int, float)) or isinstance(raw, bool):
            raise ValueError(f"{name}: valor no numérico: {raw!r}")
        value = float(raw)
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name}: fuera de rango [0,1]: {value}")
        dimensions.append(DimensionValue(name=name, value=value, present=True,
                                         source=(sources or {}).get(name, "")))
        weighted_sum += w[name] * value
        weight_total += w[name]

    present_count = sum(1 for d in dimensions if d.present)
    composite = weighted_sum / weight_total if weight_total else 0.0
    coverage = Coverage.FULL if present_count == len(DIMENSIONS) else (
        Coverage.PARTIAL if present_count >= 7 else Coverage.WEAK
    )
    unknown = tuple(d.name for d in dimensions if not d.present)
    return MCDAResult(composite=composite, coverage=coverage,
                      present_count=present_count,
                      dimensions=tuple(dimensions), unknown_dimensions=unknown)
