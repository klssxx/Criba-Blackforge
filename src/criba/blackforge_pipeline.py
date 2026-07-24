"""BLACKFORGE headless pipeline — FASE 5 (PACKET 2.1) + FASE 6 (PIPELINE HEADLESS).

Deterministic, PySide6-free orchestration over the immutable BLACKFORGE catalog:

    selector -> safety gate -> per-item causal signal -> measurement (CCA +
    convergence) -> ranked ideas -> packet 2.1 + normalized output.

The convergence formula (value_score = evidence*novelty/cost) is the SAME one
used by the CRIBA engine (src/criba/engine.py _evaluate_idea) and is NOT
re-derived here; it is imported so the two engines stay in lockstep (FASE 7
regression guarantees CRIBA is untouched).

Output artifacts (FASE 6):
- verification/blackforge_headless_output.json
- verification/blackforge_headless_output.normalized.json  (no UUID/timestamp/path)
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

from .blackforge_catalog import load as _load_catalog, get as _get
from .blackforge_selector import select_blackforge
from .blackforge_safety import evaluate_blackforge_safety, DENY
from .engine import _evaluate_idea, _clamp

REFERENCE_QUERY = (
    "¿Cómo podemos generar ideas estructuralmente nuevas para controlar las acciones "
    "de agentes autónomos sin depender de una autoridad central permanente?"
)

PACKET_SCHEMA = "blackforge_headless_packet"
PACKET_VERSION = "2.1.0"


def run_headless(
    query: str = REFERENCE_QUERY,
    seed: int = 1,
    session_size: int = 12,
    profile: str = "hybrid",
    session_context: Optional[Mapping[str, Any]] = None,
    session_id: str = "blackforge-headless",
) -> Dict[str, Any]:
    """Run the full headless pipeline and return a packet-2.1 dict."""
    sel = select_blackforge(seed=seed, session_size=session_size, profile=profile)
    if sel.failure is not None:
        # Honest: surface the selection failure, do not fabricate ideas.
        return {
            "schema": PACKET_SCHEMA,
            "schema_version": PACKET_VERSION,
            "query": query,
            "selection": sel.to_dict(),
            "ideas": [],
            "status": "SELECTION_FAILED",
        }

    ctx: Dict[str, Any] = dict(session_context or {})
    selected_items: List[Mapping[str, Any]] = [
        x for x in (_get(bid) for bid in sel.selected_ids) if x is not None
    ]

    # Safety gate: keep only items that are NOT DENY.
    safe: List[Mapping[str, Any]] = []
    safety_report: List[Dict[str, Any]] = []
    for raw_item in selected_items:
        d = evaluate_blackforge_safety(dict(raw_item), ctx, session_id=session_id)
        safety_report.append(d.to_dict())
        if d.decision != DENY:
            safe.append(raw_item)

    # Build ideas with a causal signal + convergence measurement.
    ideas: List[Dict[str, Any]] = []
    seen_axes: Dict[str, int] = {}
    for idx, raw_item in enumerate(safe, start=1):
        record: Mapping[str, Any] = raw_item
        axis = record.get("causal_axis_primary") or "unknown"
        # novelty: how many distinct causal axes are represented among survivors
        # (measurement-layer datum, same spirit as CRIBA's CCA).
        seen_axes[axis] = seen_axes.get(axis, 0) + 1
        # Divergence surrogate: distinct axis vs the count already seen.
        # Build a CRIBA-like idea dict so _evaluate_idea stays the single source.
        idea = {
            "id": f"BF{idx:02d}",
            "blackforge_id": record["blackforge_id"],
            "title": record.get("title", ""),
            "description": record.get("description", ""),
            "causal_variables": {axis: record.get("causal_axis_primary", "unknown")},
            "extreme": bool(record.get("requires_explicit_authorization")),
            "genome": {
                "actor": [record.get("source_family", "unknown")],
                "mechanism": [record.get("functional_category_primary", "capability_proof")],
                "topology": [record.get("domain_primary", "unknown")],
                "trust_model": ["evidence_based" if record.get("evidence_level") == "testable" else "implicit"],
                "time_model": ["staged"],
            },
            "causal_axis_primary": axis,
            "pipeline_stage": record.get("pipeline_stage"),
            "safety_class": record.get("safety_class"),
            "quality_score_v2": record.get("quality_score_v2", 0),
        }
        conv = _evaluate_idea(idea)  # same convergence formula as CRIBA engine
        idea["convergence"] = conv
        idea["causal_signature_present"] = axis != "unknown"
        ideas.append(idea)

    # CCA-style: drop "cosmetic" survivors (no distinct causal axis moved).
    real = [i for i in ideas if i["causal_signature_present"]]
    cosmetic = len(ideas) - len(real)

    # Rank by value_score (desc) — keep canonical collection ordered.
    ranked = sorted(real, key=lambda x: x["convergence"]["value_score"], reverse=True)
    ranked[:] = ranked
    top_ideas = [i["id"] for i in ranked[:3]]
    mean_value = round(
        sum(i["convergence"]["value_score"] for i in ranked) / max(1, len(ranked)), 4
    )

    # Measurement summary (FASE 6 checks).
    metrics = {
        "potential_novelty": _clamp(60 + len(real) * 4),
        "divergence": _clamp(40 + 12 * min(len(real), 8)),
        "feasibility": _clamp(60),
        "controlled_risk": _clamp(48),
        "reversibility": _clamp(74),
        "uncertainty": _clamp(56),
        "mean_value_score": mean_value,
    }

    packet = {
        "schema": PACKET_SCHEMA,
        "schema_version": PACKET_VERSION,
        "activation_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "session_id": session_id,
        "selection": sel.to_dict(),
        "safety_report": safety_report,
        "causal_axes_represented": sorted(seen_axes.keys()),
        "ideas": ranked,
        "real_divergent_count": len(real),
        "cosmetic_rejected": cosmetic,
        "top_ideas": top_ideas,
        "mean_value_score": mean_value,
        "metrics": metrics,
        "status": "OK",
    }
    return packet


def _stable(packet: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize for golden comparison: drop UUID/timestamp/paths, sort keys."""
    p = {k: v for k, v in packet.items() if k not in ("activation_id", "timestamp")}
    p = _strip_timestamps(p)
    stable: Dict[str, Any] = json.loads(json.dumps(p, ensure_ascii=False, sort_keys=True))
    return stable


def _strip_timestamps(obj: Any) -> Any:
    """Recursively drop 'timestamp' keys so normalized output is deterministic."""
    if isinstance(obj, dict):
        return {k: _strip_timestamps(v) for k, v in obj.items() if k != "timestamp"}
    if isinstance(obj, list):
        return [_strip_timestamps(v) for v in obj]
    return obj


def save_artifacts(packet: Dict[str, Any], out_dir: str = "verification") -> Dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    raw_path = os.path.join(out_dir, "blackforge_headless_output.json")
    norm_path = os.path.join(out_dir, "blackforge_headless_output.normalized.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(packet, f, ensure_ascii=False, indent=2)
    with open(norm_path, "w", encoding="utf-8") as f:
        json.dump(_stable(packet), f, ensure_ascii=False, indent=2)
    return {"raw": raw_path, "normalized": norm_path}
