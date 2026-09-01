"""Genome similarity and duplicate detection (local, deterministic).

Rules (condition 14 — mandatory unknown handling):
- Multivalue fields: remove 'unknown' BEFORE Jaccard. unknown cannot raise
  numerator or denominator.
- If both effective sets are empty -> field similarity 0.0 (not 1.0).
- Single-value field with 'unknown' on either side -> NOT a match; treated as
  insufficient information.
- If ALL comparable fields are unknown -> global similarity 0.0.
- Two incomplete genomes are NEVER classified duplicate just for sharing absence.
- Returns similarity AND coverage, with comparable_weight, matching/different/
  unknown field lists. Duplicate classification requires coverage >= threshold.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

_RAW_WEIGHTS = {
    "mechanism": 0.30,
    "trust_model": 0.20,
    "topology": 0.15,
    "actor": 0.10,
    "time_model": 0.10,
    "incentive": 0.05,
    "scale": 0.05,
    "external_domain": 0.05,
}
# MVP minimal genome only carries these 5 dimensions. Normalize weights to those
# actually comparable so that ALL-unknown => similarity 0.0 (condition 14 rule 5).
_COMPARABLE_FIELDS = ["mechanism", "trust_model", "topology", "actor", "time_model"]
_MULTIVALUE_FIELDS = _COMPARABLE_FIELDS

_COMP_RAW = {k: _RAW_WEIGHTS[k] for k in _COMPARABLE_FIELDS}
_COMP_TOTAL = sum(_COMP_RAW.values())
WEIGHTS: dict[str, float] = {k: v / _COMP_TOTAL for k, v in _COMP_RAW.items()}

MIN_DUPLICATE_COVERAGE = 0.60

_TH = 0.85   # >= this AND same main mechanism -> probable_duplicate
_MID = 0.70  # between MID and _TH -> close_variant; below -> structurally_distinct


def _effective(values: object) -> set[str]:
    s = values if isinstance(values, list) else [values]
    return {str(x).strip().lower() for x in s if x is not None} - {"unknown"}


def _field_similarity(field: str, a: object, b: object) -> float:
    ea, eb = _effective(a), _effective(b)
    if not ea and not eb:
        return 0.0  # both absent -> no match credit
    if not ea or not eb:
        return 0.0  # one absent -> no strong match
    inter = len(ea & eb); union = len(ea | eb)
    return inter / union if union else 0.0


def genome_distance(a: Mapping[str, object], b: Mapping[str, object]) -> dict[str, Any]:
    """Weighted distance/similarity with coverage. unknown never counts as match."""
    matches: dict[str, float] = {}
    diffs: dict[str, dict[str, object | None]] = {}
    unknowns: list[str] = []
    total = 0.0
    comp_weight = 0.0
    for field, w in WEIGHTS.items():
        if field not in _MULTIVALUE_FIELDS:
            continue
        sim = _field_similarity(field, a.get(field, ["unknown"]), b.get(field, ["unknown"]))
        matches[field] = round(sim, 4)
        diffs[field] = {"a": a.get(field), "b": b.get(field)}
        total += w * (1 - sim)
        ea, eb = _effective(a.get(field, ["unknown"])), _effective(b.get(field, ["unknown"]))
        if ea or eb:
            comp_weight += w  # field carried comparable information
        else:
            unknowns.append(field)
    distance = round(total, 4)
    similarity = round(1 - distance, 4)
    coverage = round(comp_weight / _COMP_TOTAL, 4)
    return {
        "distance": distance,
        "similarity": similarity,
        "coverage": coverage,
        "comparable_weight": round(comp_weight, 4),
        "matching_fields": matches,
        "different_fields": diffs,
        "unknown_fields": unknowns,
    }


def classify(a: Mapping[str, object], b: Mapping[str, object]) -> dict[str, Any]:
    res = genome_distance(a, b)
    sim = res["similarity"]
    cov = res["coverage"]
    main_a = main_mechanism(a) or "unknown"
    main_b = main_mechanism(b) or "unknown"
    same_main = main_a == main_b and main_a != "unknown"
    if cov < MIN_DUPLICATE_COVERAGE:
        verdict = "structurally_distinct"  # insufficient info -> never duplicate
    elif sim >= _TH and same_main:
        verdict = "probable_duplicate"
    elif sim >= _MID:
        verdict = "close_variant"
    else:
        verdict = "structurally_distinct"
    reason = (f"similitud={sim}, cobertura={cov} (>= {MIN_DUPLICATE_COVERAGE} requerida para duplicado). "
              f"mismo mecanismo principal={same_main} ({main_a}).")
    res["verdict"] = verdict
    res["reason"] = reason
    return res


def main_mechanism(g: Mapping[str, object]) -> str:
    values = g.get("mechanism")
    if not isinstance(values, list) or not values:
        return ""
    m = str(values[0])
    return m if m != "unknown" else ""
