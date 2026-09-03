"""P04 retrieval tests: lexical BM25, expansion, dedup/RRF/rerank, recursive."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from criba.intelligence import contracts as C
from criba.intelligence.retrieval.expansion import QueryExpander
from criba.intelligence.retrieval.hybrid import (Deduper, reciprocal_rank_fusion,
                                                 rerank_diversity)
from criba.intelligence.retrieval.lexical import LexicalIndex, tokenize
from criba.intelligence.retrieval.recursive import (RecursiveSearcher,
                                                    backward_citations,
                                                    forward_citations)
from criba.intelligence.storage import IntelligenceStore


def _doc(title, abstract, sid="openalex", did=None):
    return C.EvidenceDocument(doc_id=did or f"d_{title[:8].replace(' ', '_')}",
                              source_id=sid, title=title, kind="paper",
                              abstract=abstract)


DOCS = [
    _doc("Photonic cooling breakthrough", "photonic cooling reduces energy in datacenter racks"),
    _doc("Liquid cooling loops", "liquid cooling loop design for servers energy"),
    _doc("Unrelated biology", "photosynthesis in plants under light"),
    _doc("Datacenter thermal study", "thermal management datacenter energy efficiency pue"),
]


@pytest.fixture()
def store(tmp_path):
    s = IntelligenceStore(tmp_path / "i.sqlite3")
    for d in DOCS:
        s.save_document(d.to_dict())
    yield s
    s.close()


def test_tokenize_stops_and_case():
    assert "the" not in tokenize("The cooling of the datacenter")
    assert tokenize("Cooling!") == ["cooling"]


def test_bm25_ranks_relevant_first(store):
    idx = LexicalIndex(store).build()
    assert idx.doc_count() == 4
    hits = idx.search("photonic cooling datacenter")
    assert hits[0].doc_id == "d_Photonic"
    assert hits[0].score > 0
    # biology doc should not appear for this query
    ids = [h.doc_id for h in idx.search("photonic cooling datacenter")]
    assert "d_Unrelated" not in ids


def test_query_expansion_synonyms_and_ml():
    eq = QueryExpander().expand("cheap cooling for datacenter")
    texts = " | ".join(eq.texts())
    assert "low cost" in texts            # T033
    assert "immersion cooling" in texts or "radiative cooling" in texts  # T034
    assert any(v.language == "es" for v in eq.variants)  # T035
    assert len(eq.variants) <= 12


def test_query_mutation_drops_failing_terms():
    qe = QueryExpander()
    muts = qe.mutate("photonic cooling apparatus", prior_terms=["cooling"])
    assert muts and all(v.origin == "mutation" for v in muts)


def test_dedupe_jaccard_collapses_near_duplicates():
    d1 = _doc("A study of photonic cooling A", "photonic cooling datacenter energy")
    d2 = _doc("A study of photonic cooling B", "photonic cooling datacenter energy wasted")
    d3 = _doc("Totally different topic", "quantum error correction codes")
    out = Deduper().dedupe([d1, d2, d3])
    assert len(out) == 2  # d1/d2 near-dup -> one kept


def test_rrf_fuses_two_source_lists():
    a = [_doc("Paper A", "x", sid="openalex"), _doc("Paper B", "y", sid="openalex")]
    b = [_doc("Paper B", "y", sid="github", did="gh_1"), _doc("Paper C", "z", sid="github", did="gh_2")]
    fused = reciprocal_rank_fusion([a, b])
    top_ids = [f.doc.doc_id for f in fused]
    assert "d_Paper_B" in top_ids or "gh_1" in top_ids
    top = fused[0]
    assert top.score > 0 and len(top.ranks) >= 1


def test_rrf_cross_source_same_paper_ranks_high():
    a = [_doc("Shared topic", "content", sid="openalex")]
    b = [_doc("Shared topic", "content", sid="arxiv", did="ax_1")]
    fused = reciprocal_rank_fusion([a, b])
    assert len(fused) == 2  # two doc_ids but both rank 1 -> top scores equal
    assert fused[0].score == fused[1].score


def test_rerank_caps_source_dominance():
    docs = [_doc(f"repo {i}", "content", sid="github") for i in range(8)]
    docs += [_doc("paper key", "content", sid="openalex")]
    fused = reciprocal_rank_fusion([docs])
    rr = rerank_diversity(fused, per_source_cap=5)
    top6_sources = [f.doc.source_id for f in rr[:6]]
    assert top6_sources.count("github") <= 5


def test_recursive_search_expands_and_stops(store):
    idx = LexicalIndex(store).build()
    def searcher(q, n):
        out = []
        for h in idx.search(q, n):
            d = store.get_document(h.doc_id) or {}
            out.append(C.EvidenceDocument(
                doc_id=d["doc_id"], source_id=d["source_id"], title=d["title"],
                kind=d["kind"], abstract=d["abstract"], published=d["published"],
                url=d["url"], language=d["language"], metadata=d.get("metadata") or {}))
        return out
    rs = RecursiveSearcher(searcher, max_depth=2, max_queries=5)
    rep = rs.run("datacenter cooling")
    assert rep.rounds >= 1
    assert rep.stop_reason in ("max_queries", "max_depth", "no_new_documents", "no_results")
    assert len(rep.documents) >= 2
    assert all(rep.queries_used)


def test_citations_traversal():
    base = _doc("Base paper", "base", did="base")
    base.metadata["references"] = ["ref_1", "ref_2"]
    citing = _doc("Citing paper", "cites base", did="citer")
    citing.metadata["references"] = ["base"]
    assert backward_citations(base) == ["ref_1", "ref_2"]
    assert [d.doc_id for d in forward_citations(base, [base, citing])] == ["citer"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
