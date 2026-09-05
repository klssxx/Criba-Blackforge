"""P01-T05 tests: registry integrity (addendum §106-§113 mandatory tests)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from criba.intelligence.registry import TechniqueRegistry

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "data" / "intelligence" / "technique_registry.yaml"


@pytest.fixture(scope="module")
def reg() -> TechniqueRegistry:
    return TechniqueRegistry(REGISTRY_PATH)


def test_all_130_techniques_registered(reg):
    """§106: count == 130 and ids == T001..T130."""
    ids = [t.id for t in reg.all()]
    assert ids == [f"T{i:03d}" for i in range(1, 131)]
    assert reg.count() == 130


def test_all_techniques_have_canonical_owner(reg):
    """§107."""
    valid = {"CRIBA", "CRIBA_IIE", "BLACKFORGE", "SUPRA_ORCHESTRATION", "CRIBA_PLUS_SUPRA", "CRIBA_PLUS_IIE"}
    bad = [t.id for t in reg.all() if t.owner not in valid]
    assert bad == [], f"unknown owners: {bad}"


def test_all_techniques_have_execution_pipeline(reg):
    """§108: no REGISTERED_BUT_ORPHANED."""
    orphans = [t.id for t in reg.all() if not t.pipelines]
    assert orphans == []


def test_techniques_have_input_output_contracts(reg):
    """§112 — registry carries the slots; they get filled per-phase as
    techniques are implemented. PLANNED techniques may have empty contracts,
    but IMPLEMENTED ones must declare them."""
    bad = [t.id for t in reg.implemented()
           if not (t.input_contracts and t.output_contracts)]
    assert bad == []


def test_implemented_techniques_have_tests(reg):
    """§110."""
    bad = [t.id for t in reg.implemented() if not t.tests]
    assert bad == []


def test_technique_status_matches_runtime_capabilities(reg):
    """§113: every technique needing network+credentials but unconfigured is
    UNCONFIGURED, not IMPLEMENTED_AVAILABLE. With no credentials configured
    anywhere yet, no AUTH_NETWORK technique may claim IMPLEMENTED."""
    bad = [t.id for t in reg.implemented() if t.requires_credentials]
    assert bad == []


def test_registry_full_validate(reg):
    """Aggregate of all §106-§113 checks via registry.validate()."""
    errors = reg.validate()
    assert errors == [], f"registry integrity errors: {errors}"


def test_by_pipeline_and_family(reg):
    assert len(reg.by_pipeline("PRIOR_ART")) >= 10
    assert len(reg.by_family("PATENT_INTELLIGENCE")) == 9
    assert len(reg.by_family("EXTERNAL_SOURCES")) == 21
    assert len(reg.by_family("ADVERSARIAL_FUTURES")) == 15  # T116-T130


def test_subtechniques_present(reg):
    for tid in ("T126", "T127", "T128", "T129", "T130"):
        assert reg.get(tid).subtechniques, f"{tid} missing subtechniques"


def test_supra_owns_only_orchestration(reg):
    """Addendum D: SUPRA orchestrates, never implements intelligence."""
    supra = reg.by_owner("SUPRA_ORCHESTRATION")
    assert [t.id for t in supra] == ["T120"]
    assert "orchestrat" in supra[0].module[1].lower() or "supra" in supra[0].module[1].lower()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
