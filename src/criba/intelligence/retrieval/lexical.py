"""IIE lexical retrieval (P04-T01): BM25-style scoring over FTS5 + local corpus.

Uses SQLite FTS5 rank as base; adds simple tf-idf term weighting for scores
stable across runs (no external deps, offline-friendly §104).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

from ..storage.store import IntelligenceStore

_TOKEN = re.compile(r"[a-z0-9]{2,}")
_STOP = {"the", "a", "an", "of", "for", "and", "or", "in", "on", "to", "with", "by", "is", "are", "at", "as", "be", "can", "using"}


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP]


@dataclass
class ScoredDoc:
    doc_id: str
    score: float
    title: str
    source_id: str
    kind: str


def _bm25idf(df: int, n_docs: int) -> float:
    return math.log(1 + (n_docs - df + 0.5) / (df + 0.5))


class LexicalIndex:
    """In-memory BM25-lite over stored documents (offline, deterministic)."""

    def __init__(self, store: IntelligenceStore):
        self.store = store
        self._docs: dict[str, dict] = {}
        self._tf: dict[str, dict[str, int]] = {}
        self._df: dict[str, int] = {}
        self._built = False

    def build(self) -> "LexicalIndex":
        rows = self.store._conn.execute(
            "SELECT doc_id, title, abstract, source_id, kind FROM intel_documents").fetchall()
        self._docs, self._tf, self._df = {}, {}, {}
        for r in rows:
            tokens = tokenize((r["title"] or "") + " " + (r["abstract"] or ""))
            tf: dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            self._docs[r["doc_id"]] = dict(r)
            self._tf[r["doc_id"]] = tf
            for t in tf:
                self._df[t] = self._df.get(t, 0) + 1
        self._built = True
        return self

    def ensure(self) -> "LexicalIndex":
        return self if self._built else self.build()

    def search(self, query: str, limit: int = 10) -> list[ScoredDoc]:
        self.ensure()
        q_terms = tokenize(query)
        if not q_terms:
            return []
        n = len(self._docs) or 1
        k1, b = 1.5, 0.75
        avg_len = (sum(len(tf) for tf in self._tf.values()) / n) if n else 0.0
        scores: list[tuple[float, str]] = []
        for doc_id, tf in self._tf.items():
            s = 0.0
            dl = len(tf)
            for t in q_terms:
                f = tf.get(t, 0)
                if not f:
                    continue
                idf = _bm25idf(self._df.get(t, 0), n)
                s += idf * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / (avg_len or 1)))
            if s > 0:
                scores.append((s, doc_id))
        scores.sort(reverse=True)
        return [ScoredDoc(doc_id=did, score=s, title=self._docs[did]["title"],
                          source_id=self._docs[did]["source_id"], kind=self._docs[did]["kind"])
                for s, did in scores[:limit]]

    def doc_count(self) -> int:
        self.ensure()
        return len(self._docs)
