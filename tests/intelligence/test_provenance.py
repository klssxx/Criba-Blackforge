"""P05 tests: epistemic semantics (§102), content_hash, claims extraction,
entity resolution/aliases/merge."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from criba.intelligence import contracts as C
from criba.intelligence.claims import extract_claims_from_fragments
from criba.intelligence.entities import EntityResolver, extract_entities
from criba.intelligence.provenance import ProvenanceValidator, assess_claims, content_hash


def _doc(frag_texts=("Photonic cooling reduces energy use by 42 percent",),
         doc_id="d1"):
    return C.EvidenceDocument(
        doc_id=doc_id, source_id="openalex", title="T",
        fragments=[C.EvidenceFragment(text=t) for t in frag_texts])


def test_fact_without_evidence_is_downgraded():
    doc = _doc()
    claims = [
        C.Claim(text="grounded fact", epistemic_state=C.EpistemicState.FACT,
                evidence_doc_ids=("d1",)),
        C.Claim(text="ungrounded fact", epistemic_state=C.EpistemicState.FACT,
                evidence_doc_ids=("missing_doc",)),
    ]
    assessments, ratio = assess_claims(claims, [doc])
    assert claims[0].epistemic_state == C.EpistemicState.FACT      # stays
    assert claims[1].epistemic_state == C.EpistemicState.INFERENCE  # downgraded
    assert assessments[1].notes.startswith("downgraded")
    assert ratio == 0.5


def test_ratio_all_grounded():
    doc = _doc()
    claims = [C.Claim(text="a", evidence_doc_ids=("d1",)),
              C.Claim(text="b", evidence_doc_ids=("d1",))]
    _, ratio = assess_claims(claims, [doc])
    assert ratio == 1.0


def test_content_hash_stable_and_sensitive():
    d1 = _doc(doc_id="x")
    d2 = _doc(doc_id="y")  # different id, same content -> same hash
    d3 = _doc(frag_texts=("different text",), doc_id="x")
    assert content_hash(d1) == content_hash(d2)
    assert content_hash(d1) != content_hash(d3)


def test_claim_extraction_rules():
    doc = _doc(frag_texts=(
        "Photonic cooling reduces energy use in racks",
        "Nothing matching here",
        "The system fails under high humidity",
    ))
    claims = extract_claims_from_fragments(doc)
    assert len(claims) == 2
    assert all(c.created_by == "rule" for c in claims)
    assert all(c.evidence_doc_ids == (doc.doc_id,) for c in claims)
    assert any("reduces" in c.text for c in claims)
    assert any("fails" in c.text for c in claims)


def test_entity_resolver_dedup_and_aliases():
    r = EntityResolver()
    a = r.resolve("Photonic Cooling", node_type="Technology", source_doc_id="d1")
    b = r.resolve("photonic cooling")  # same normalized label -> same node
    assert a.entity_id == b.entity_id
    assert r.count() == 1
    r.add_alias(a.entity_id, "optical refrigeration")
    c = r.resolve("Optical Refrigeration")  # via alias
    assert c.entity_id == a.entity_id
    assert r.count() == 1


def test_entity_merge_repoints_keys():
    r = EntityResolver()
    a = r.resolve("Liquid Cooling")
    b = r.resolve("Direct Liquid Cooling")
    r.add_alias(b.entity_id, "dlc")
    merged = r.merge(a.entity_id, b.entity_id)
    assert merged == a.entity_id
    assert r.resolve("dlc").entity_id == a.entity_id  # alias repointed
    assert r.count() == 1


def test_entity_resolution_is_type_aware_and_cross_type_merge_is_rejected():
    r = EntityResolver()
    technology = r.resolve("OpenAlex", node_type="Technology")
    organization = r.resolve("OpenAlex", node_type="Organization")
    assert technology.entity_id != organization.entity_id
    with pytest.raises(ValueError, match="different node types"):
        r.merge(technology.entity_id, organization.entity_id)


def test_gazetteer_extraction():
    r = EntityResolver()
    nodes = extract_entities(
        "Immersion cooling in the data center reduces waste heat", r, source_doc_id="d1")
    labels = {n.label for n in nodes}
    assert "immersion cooling" in labels
    assert "data center" in labels or "datacenter" in labels
    assert all(n.source_doc_ids == ("d1",) for n in nodes)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
