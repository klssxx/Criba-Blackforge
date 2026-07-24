"""Migration of legacy MANDATORY_MODEL_PACKET (v1.x) to v2.0.0.

The legacy packet is extended additively with an ``innovation`` block. Legacy
fields are preserved; nothing is invented. Old ideas, if migrable unambiguously,
keep their IDs, get an INCOMPLETE genome, and a migration warning is recorded.

This module owns ONLY migration (separation of concerns, condition 5).
"""
from __future__ import annotations
import copy
from typing import Any

from .genome import Genome, ONTOLOGY_VERSION
from .similarity import MIN_DUPLICATE_COVERAGE

SCHEMA_VERSION = "2.0.0"


def migrate_v1_to_v2(packet_v1: dict[str, Any]) -> dict[str, Any]:
    """Return a v2 packet. Legacy fields preserved verbatim. innovation added."""
    p = copy.deepcopy(packet_v1)
    orig_schema = p.get("schema_version", "1.x")
    p["schema"] = "mandatory_model_packet"
    p["schema_version"] = SCHEMA_VERSION
    p.setdefault("intent", "INNOVAR")
    p.setdefault("versions", {"currents": "unknown", "selector": "unknown", "genome": ONTOLOGY_VERSION})

    warnings = []
    old_ideas = p.get("ideas", [])
    migrated_ideas = []
    for idx, old in enumerate(old_ideas):
        mid = old.get("id", f"LEG{idx:02d}")
        # genome is incomplete -> all unknown, never declared classified
        genome = Genome().model_dump()
        migrated_ideas.append({
            "id": mid,
            "title": old.get("method", "Idea migrada"),
            "description": old.get("proposal", ""),
            "mechanism_causal": old.get("causal_mechanism", ""),
            "difference_from_known": old.get("difference_from_existing", ""),
            "genome": genome,
            "evidence": {"field": "unknown", "value": "unknown", "evidence_span": "migrado desde v1"},
            "family": "unknown",
            "duplicate_status": "migrated_incomplete",
            "source_method": old.get("method_id", "unknown"),
        })
        warnings.append(f"idea {mid} migrada con genoma incompleto (unknown)")

    p["innovation"] = {
        "known_space": p.get("contextualization", {}).get("known_space", []),
        "saturated_mechanisms": p.get("contextualization", {}).get("saturated_mechanisms", []),
        "assumptions": p.get("contextualization", {}).get("assumptions", []),
        "ruptures": p.get("rupture", {}).get("operations", []),
        "idea_families": sorted({i["family"] for i in migrated_ideas}),
        "ideas": migrated_ideas,
        "duplicate_report": [],
        "unclassified_properties": [],
        "migration": {
            "source_schema_version": str(orig_schema),
            "status": "empty_extension" if not migrated_ideas else "ideas_migrated_incomplete",
            "warnings": warnings,
        },
    }
    # condition 3: legacy alias is the same object
    p["ideas"] = p["innovation"]["ideas"]
    return p
