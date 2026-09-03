"""IIE dedup + fusion + rerank (P04, T032 hybrid base).

dedup: (title-sig, year) + near-dup by token Jaccard.
fusion: RRF (Reciprocal Rank Fusion) — deterministic, weight per source.
rerank: source-diversity boost (§38 source_diversity dimension).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..contracts import EvidenceDocument
from .lexical import tokenize

_SIG_STRIP = re.compile(r"[^a-z0-9 ]")


def title_signature(title: str) -> str:
    return " ".join(sorted(tokenize(title))[:8])


@dataclass
class FusedResult:
    doc: EvidenceDocument
    score: float
    ranks: list[tuple[str, int]]  # (source_id, rank_in_that_list)


class Deduper:
    """T-dedup: exact signature + Jaccard near-duplicate collapse."""

    def __init__(self, jaccard_threshold: float = 0.75):
        self.threshold = jaccard_threshold

    def dedupe(self, docs: list[EvidenceDocument]) -> list[EvidenceDocument]:
        kept: list[EvidenceDocument] = []
        kept_tokens: list[set[str]] = []
        for d in sorted(docs, key=lambda x: x.title or ""):
            toks = set(tokenize((d.title or "") + " " + (d.abstract or "")[:300]))
            dup = False
            for kt in kept_tokens:
                inter = len(toks & kt)
                union = len(toks | kt) or 1
                if inter / union >= self.threshold:
                    dup = True
                    break
            if not dup:
                kept.append(d)
                kept_tokens.append(toks)
        return kept


def reciprocal_rank_fusion(result_lists: list[list[EvidenceDocument]],
                           k: int = 60, weights: list[float] | None = None
                           ) -> list[FusedResult]:
    """RRF: robust to score-scale differences across sources (T032 fusion)."""
    if weights is None:
        weights = [1.0] * len(result_lists)
    agg: dict[str, FusedResult] = {}
    for w, lst in zip(weights, result_lists):
        for rank, doc in enumerate(lst, start=1):
            contribution = w / (k + rank)
            if doc.doc_id in agg:
                agg[doc.doc_id].score += contribution
                agg[doc.doc_id].ranks.append((doc.source_id, rank))
            else:
                agg[doc.doc_id] = FusedResult(doc=doc, score=contribution,
                                              ranks=[(doc.source_id, rank)])
    return sorted(agg.values(), key=lambda f: f.score, reverse=True)


def rerank_diversity(fused: list[FusedResult], per_source_cap: int = 5) -> list[FusedResult]:
    """Boost diversity: cap same-source dominance in top results."""
    counts: dict[str, int] = {}
    head: list[FusedResult] = []
    tail: list[FusedResult] = []
    for f in fused:
        sid = f.doc.source_id
        if counts.get(sid, 0) < per_source_cap:
            counts[sid] = counts.get(sid, 0) + 1
            head.append(f)
        else:
            tail.append(f)
    return head + tail
