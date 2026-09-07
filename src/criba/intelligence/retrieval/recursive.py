"""IIE recursive search (P04-T06) + citation chasing hooks (T038/T039).

Recursive: iterate retrieve->expand (entities/terms from top docs) up to
max_depth, respecting budget. Deterministic, offline (works over local store).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

from ..contracts import EvidenceDocument
from .expansion import QueryExpander
from .hybrid import Deduper, FusedResult, reciprocal_rank_fusion, rerank_diversity
from .lexical import LexicalIndex, tokenize

_SEARCHER = Callable[[str, int], list[EvidenceDocument]]


@dataclass
class RecursiveReport:
    rounds: int = 0
    queries_used: list[str] = field(default_factory=list)
    documents: list[EvidenceDocument] = field(default_factory=list)
    expansion_terms: list[str] = field(default_factory=list)
    stop_reason: str = ""


class RecursiveSearcher:
    """T037: retrieve -> extract salient terms -> re-query -> fuse. Stop when
    (a) max_depth, (b) no new documents, (c) budget/max_queries."""

    def __init__(self, searcher: _SEARCHER, max_depth: int = 2,
                 max_queries: int = 8, new_doc_bonus_threshold: int = 0,
                 expander: QueryExpander | None = None):
        self.searcher = searcher
        self.max_depth = max_depth
        self.max_queries = max_queries
        self.expander = expander or QueryExpander()

    def _salient_terms(self, docs: list[EvidenceDocument], known: Counter[str],
                       top: int = 3) -> list[str]:
        c: Counter[str] = Counter()
        for d in docs[:5]:
            for t in tokenize((d.title or "") + " " + (d.abstract or "")[:400]):
                c[t] += 1
        return [t for t, _ in c.most_common(15)
                if t not in known and len(t) > 4][:top]

    def run(self, query: str, limit_per_query: int = 8) -> RecursiveReport:
        rep = RecursiveReport()
        seen_ids: set[str] = set()
        all_docs: list[EvidenceDocument] = []
        queries = [query]
        known_terms: Counter[str] = Counter(tokenize(query))

        for depth in range(self.max_depth):
            round_docs: list[EvidenceDocument] = []
            for q in list(queries):
                if len(rep.queries_used) >= self.max_queries:
                    rep.stop_reason = "max_queries"
                    break
                docs = self.searcher(q, limit_per_query)
                round_docs.extend(docs)
                rep.queries_used.append(q)
            if not round_docs:
                rep.stop_reason = "no_results"
                break
            deduped = Deduper().dedupe(round_docs)
            new = [d for d in deduped if d.doc_id not in seen_ids]
            rep.rounds += 1
            for d in new:
                seen_ids.add(d.doc_id)
                all_docs.append(d)
            if not new:
                rep.stop_reason = "no_new_documents"
                break
            if len(rep.queries_used) >= self.max_queries:
                rep.stop_reason = "max_queries"
                break
            terms = self._salient_terms(new, known_terms)
            rep.expansion_terms.extend(terms)
            for t in terms:
                known_terms[t] += 1
            queries = [f"{query} {t}" for t in terms]
        else:
            rep.stop_reason = "max_depth"
        rep.documents = all_docs
        if not rep.stop_reason:
            rep.stop_reason = "done"
        return rep


# -- citation chasing (T038/T039) --------------------------------------------
# Real citation edges arrive with P05/P06 (entities/relations). Here we define
# the traversal contract over reference lists already present in metadata.

def backward_citations(doc: EvidenceDocument) -> list[str]:
    """T038: docs this work cites (references list in metadata)."""
    refs = (doc.metadata or {}).get("references") or []
    return list(refs)


def forward_citations(doc: EvidenceDocument, corpus: list[EvidenceDocument]) -> list[EvidenceDocument]:
    """T039: docs in corpus whose references include this doc's id/doi."""
    keys = {doc.doc_id, (doc.metadata or {}).get("doi"), doc.url} - {None, ""}
    out = []
    for other in corpus:
        if other.doc_id == doc.doc_id:
            continue
        refs = set((other.metadata or {}).get("references") or [])
        if refs & keys:
            out.append(other)
    return out
