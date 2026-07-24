"""FASE 1 — INGESTA DEL CATÁLOGO BLACKFORGE (gate reproducible).

Validates the consolidated 723-record catalog against its OWN embedded
policies (taxonomy_policy / safety_policy / selection_policy) and emits a
machine-readable report to verification/blackforge_catalog_report.json.

Load-bearing invariants (per HIPER_MEGAPROMPT FASE 1):
- 723 records present;
- blackforge_id and source_ref are globally unique;
- tier quotas match activation_tier (the canonical quota source) exactly;
- safety classes, pipeline stages and functional categories are within the
  declared enums;
- loader is immutable (records are MappingProxyType, not mutatable in place);
- any divergence is REPORTED, never silently fixed.

The report is NOT auto-updated on failure; if a contract breaks, the test
fails loudly so a human decides (mirrors the golden-master policy).
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from types import MappingProxyType

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from criba import blackforge_catalog as bc  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
REPORT = os.path.join(ROOT, "verification", "blackforge_catalog_report.json")

# ---------------------------------------------------------------------------
# Reusable validation (also drives the report written by test_emits_report).
# ---------------------------------------------------------------------------

def _validate():
    meta, recs = bc.load()
    tax = meta.get("taxonomy_policy", {})
    valid_tiers = set(tax.get("activation_tiers", []))
    valid_safety = set(tax.get("safety_classes", []))
    valid_stages = set(tax.get("pipeline_stages", []))
    valid_fcats = set(tax.get("functional_categories", []))

    ids = [r["blackforge_id"] for r in recs]
    srefs = [r["source_ref"] for r in recs]
    canon = [r.get("canonical_item_id") for r in recs]

    id_dups = [k for k, c in Counter(ids).items() if c > 1]
    sref_dups = [k for k, c in Counter(srefs).items() if c > 1]
    canon_dups = {k: c for k, c in Counter(canon).items() if c > 1}

    act_tier_counts = Counter(r.get("activation_tier") for r in recs)
    meta_tier_counts = dict(meta.get("tier_counts", {}))
    tier_quota_ok = dict(act_tier_counts) == meta_tier_counts

    tier_field_counts = Counter(r.get("tier") for r in recs)
    tier_field_vs_activation_mismatch = sum(
        1 for r in recs if r.get("tier") != r.get("activation_tier")
    )

    bad_safety = sorted({r["safety_class"] for r in recs if r["safety_class"] not in valid_safety})
    bad_stage = sorted({r["pipeline_stage"] for r in recs if r["pipeline_stage"] not in valid_stages})
    bad_stage_primary = sorted({r.get("stage_primary") for r in recs if r.get("stage_primary") and r.get("stage_primary") not in valid_stages})
    bad_fcat = sorted({r["functional_category"] for r in recs if r["functional_category"] not in valid_fcats})

    return {
        "record_count": len(recs),
        "meta_record_count": meta.get("record_count"),
        "unique_blackforge_id": len(set(ids)),
        "unique_source_ref": len(set(srefs)),
        "unique_canonical_item_id": len(set(canon)),
        "blackforge_id_duplicates": id_dups,
        "source_ref_duplicates": sref_dups,
        "canonical_item_id_duplicates": canon_dups,
        "activation_tier_counts": dict(act_tier_counts),
        "meta_tier_counts": meta_tier_counts,
        "tier_quota_matches_activation_tier": tier_quota_ok,
        "tier_field_counts": dict(tier_field_counts),
        "tier_field_vs_activation_tier_mismatch": tier_field_vs_activation_mismatch,
        "safety_class_out_of_enum": bad_safety,
        "pipeline_stage_out_of_enum": bad_stage,
        "stage_primary_out_of_enum": bad_stage_primary,
        "functional_category_out_of_enum": bad_fcat,
        "valid_safety_classes": sorted(valid_safety),
        "valid_pipeline_stages": sorted(valid_stages),
        "valid_functional_categories": sorted(valid_fcats),
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_record_count_is_723():
    _, recs = bc.load()
    assert len(recs) == 723


def test_blackforge_id_and_source_ref_unique():
    v = _validate()
    assert v["unique_blackforge_id"] == 723, v["blackforge_id_duplicates"]
    assert v["unique_source_ref"] == 723, v["source_ref_duplicates"]


def test_tier_quota_matches_activation_tier():
    v = _validate()
    # activation_tier is the canonical quota source and must equal meta tier_counts.
    assert v["tier_quota_matches_activation_tier"], (
        v["activation_tier_counts"], v["meta_tier_counts"]
    )


def test_safety_classes_valid():
    v = _validate()
    assert v["safety_class_out_of_enum"] == [], v["safety_class_out_of_enum"]


def test_pipeline_stages_valid():
    v = _validate()
    assert v["pipeline_stage_out_of_enum"] == [], v["pipeline_stage_out_of_enum"]
    assert v["stage_primary_out_of_enum"] == [], v["stage_primary_out_of_enum"]


def test_functional_categories_valid():
    v = _validate()
    assert v["functional_category_out_of_enum"] == [], v["functional_category_out_of_enum"]


def test_loader_is_immutable():
    meta, recs = bc.load()
    # Metadata, nested policies, records and their nested collections are frozen.
    assert "records" not in meta
    assert isinstance(meta["selection_policy"], MappingProxyType)
    with pytest.raises(TypeError):
        meta["selection_policy"]["constraints"]["minimum_source_catalogs"] = 99
    with pytest.raises(AttributeError):
        meta["selection_policy"]["allowed_tiers_default"].append("archive")
    assert isinstance(recs, tuple)
    assert isinstance(recs[0], MappingProxyType)
    with pytest.raises(TypeError):
        recs[0]["tier"] = "mutated"
    # The frozen tuple rejects mutation (AttributeError because tuples have no
    # append; either way it is immutable).
    with pytest.raises((TypeError, AttributeError)):
        recs.append("x")


def test_loader_reuses_catalog_and_immutable_id_index():
    bc.reset_cache()
    loaded = bc.load()
    _, recs = loaded
    index = bc._get_id_index()

    assert bc.load() is loaded
    assert bc._get_id_index() is index
    assert isinstance(index, MappingProxyType)
    assert len(index) == 723
    assert bc.get(recs[-1]["blackforge_id"]) is recs[-1]
    with pytest.raises(TypeError):
        index["BF-MUTATED"] = recs[0]


def test_emits_report():
    """Write the machine-readable report (FASE 1 deliverable)."""
    v = _validate()
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    report = {
        "phase": "FASE 1 — INGESTA DEL CATÁLOGO",
        "catalog_source": "imports/blackforge_v2/criba_blackforge_catalogo_final_debate20.json",
        "validated_against": "catalog-embedded taxonomy_policy/safety_policy/selection_policy",
        "contracts": v,
        "summary": {
            "records": v["record_count"],
            "blackforge_id_unique": v["unique_blackforge_id"] == 723,
            "source_ref_unique": v["unique_source_ref"] == 723,
            "tier_quota_ok": v["tier_quota_matches_activation_tier"],
            "safety_enum_ok": v["safety_class_out_of_enum"] == [],
            "stage_enum_ok": v["pipeline_stage_out_of_enum"] == [] and v["stage_primary_out_of_enum"] == [],
            "fcat_enum_ok": v["functional_category_out_of_enum"] == [],
            # informational divergences (not contract-breaking):
            "tier_field_vs_activation_tier_mismatch": v["tier_field_vs_activation_tier_mismatch"],
            "canonical_item_id_nonunique_groups": len(v["canonical_item_id_duplicates"]),
        },
    }
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    assert os.path.exists(REPORT)
    # The report must reflect the real, current catalog (no auto-fake).
    with open(REPORT, encoding="utf-8") as f:
        back = json.load(f)
    assert back["summary"]["records"] == 723
