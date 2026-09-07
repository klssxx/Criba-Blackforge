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


def test_v2_registry_carries_traceability(reg):
    """Esquema v2: versión del canon y procedencia legibles por máquina."""
    import yaml

    raw = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    assert isinstance(raw, dict) and raw["schema_version"] == 2
    assert isinstance(raw["canon_version"], str) and raw["canon_version"].strip()
    prov = raw["provenance"]
    assert prov["source"] and "130 TECNICAS" in prov["source"]
    assert prov["generator"].endswith("gen_registry.py")
    assert len(prov["parts"]) == 4
    # la vista expone lo mismo que el YAML
    assert reg.canon_version == raw["canon_version"]
    assert reg.provenance == prov


def test_legacy_flat_list_still_loads(tmp_path):
    """Compatibilidad: un registro plano (lista) sigue cargando sin cabecera."""
    import yaml as _yaml

    from criba.intelligence.registry import TechniqueRegistry as TR

    legacy = [{"id": "T001", "name": "x", "family": "PATENT_INTELLIGENCE",
               "owner": "CRIBA_IIE", "module": ["criba.intelligence.retrieval"],
               "phase": ["P03"], "pipelines": ["DISCOVERY"],
               "status": "PLANNED", "tests": ["t"]}]
    p = tmp_path / "legacy.yaml"
    p.write_text(_yaml.safe_dump(legacy), encoding="utf-8")
    r = TR(p)
    assert r.count() == 1
    assert r.canon_version is None and r.provenance == {}


# -- qa P2-1/P2-2: carga estricta de cabecera y de entradas --------------------

VALID_ENTRY = {
    "id": "T001", "name": "x", "family": "PATENT_INTELLIGENCE",
    "owner": "CRIBA_IIE", "module": ["criba.intelligence.retrieval"],
    "phase": ["P03"], "pipelines": ["DISCOVERY"],
    "status": "PLANNED", "tests": ["t"],
}


def _v2_registry(tmp_path, *, provenance, techniques=None):
    import yaml as _yaml

    raw = {
        "schema_version": 2,
        "canon_version": "test.1",
        "provenance": provenance,
        "techniques": [dict(VALID_ENTRY)] if techniques is None else techniques,
    }
    p = tmp_path / "registry.yaml"
    p.write_text(_yaml.safe_dump(raw), encoding="utf-8")
    return p


FULL_PROVENANCE = {"source": "addendum", "generator": "gen_registry.py", "parts": ["p1.txt"]}


@pytest.mark.parametrize("provenance", [
    {},
    {"source": "s"},
    {"source": "s", "generator": "g"},
    {"source": "s", "generator": "g", "parts": []},
    {"source": "", "generator": "g", "parts": ["p"]},
    {"source": "s", "generator": None, "parts": ["p"]},
])
def test_v2_incomplete_provenance_fails_at_load(tmp_path, provenance):
    """qa P2-1: una traza v2 sin source/generator/parts no puede CARGAR;
    el fallo es ValueError en carga, no solo un reporte de validate()."""
    p = _v2_registry(tmp_path, provenance=provenance)
    with pytest.raises(ValueError, match="provenance"):
        TechniqueRegistry(p)


def test_v2_complete_provenance_still_loads(tmp_path):
    """Contraparte: la validación en carga no rompe trazas completas."""
    r = TechniqueRegistry(_v2_registry(tmp_path, provenance=FULL_PROVENANCE))
    assert r.canon_version == "test.1"
    assert r.provenance == FULL_PROVENANCE


def test_non_mapping_technique_entry_fails_at_load(tmp_path):
    """qa P2-2: techniques: ['foo'] era AttributeError crudo; ahora ValueError."""
    p = _v2_registry(tmp_path, provenance=FULL_PROVENANCE, techniques=["foo"])
    with pytest.raises(ValueError, match="entry 0 must be a mapping"):
        TechniqueRegistry(p)


@pytest.mark.parametrize("required", ["id", "name", "family", "owner"])
def test_technique_entry_missing_required_field_fails_at_load(tmp_path, required):
    """qa P2-2: falta 'id' (o name/family/owner) era KeyError crudo;
    ahora ValueError con el índice de la entrada."""
    entry = {k: v for k, v in VALID_ENTRY.items() if k != required}
    p = _v2_registry(tmp_path, provenance=FULL_PROVENANCE, techniques=[entry])
    with pytest.raises(ValueError, match=required):
        TechniqueRegistry(p)


def test_technique_entry_non_string_id_fails_at_load(tmp_path):
    entry = dict(VALID_ENTRY, id=7)
    p = _v2_registry(tmp_path, provenance=FULL_PROVENANCE, techniques=[entry])
    with pytest.raises(ValueError, match="'id'"):
        TechniqueRegistry(p)


def test_technique_entry_non_mapping_model_fails_at_load(tmp_path):
    """Misma clase de defecto: un 'model' escalar también era AttributeError."""
    entry = dict(VALID_ENTRY, model="fast")
    p = _v2_registry(tmp_path, provenance=FULL_PROVENANCE, techniques=[entry])
    with pytest.raises(ValueError, match="'model' must be a mapping"):
        TechniqueRegistry(p)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
