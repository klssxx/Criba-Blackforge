"""T081 Local novelty — distancia contra corpus declarado (corpus-local).

Solo local: sin afirmaciones de novedad global (eso es prior_art, T080).
"""
from __future__ import annotations

import re
from collections.abc import Iterable

_SPLIT = re.compile(r"[^a-z0-9áéíóúñü]+")


def _tokens(text: str) -> set[str]:
    return {t for t in _SPLIT.split((text or "").casefold()) if len(t) >= 4}


def local_novelty(candidate_text: str, corpus_texts: Iterable[str]) -> float | None:
    """1 − máxima similitud léxica (Jaccard) contra el corpus declarado.

    Corpus vacío o candidato sin tokens → None: sin referencia no hay
    novedad local medible (None ≠ 0.0: no es «idéntico», es «sin datos»).
    """
    cand = _tokens(candidate_text)
    if not cand:
        return None
    corpus = [t for t in (_tokens(c) for c in corpus_texts if c) if t]
    if not corpus:
        return None
    best = max(
        len(cand & doc) / len(cand | doc) if cand | doc else 0.0
        for doc in corpus
    )
    return round(1.0 - best, 6)
