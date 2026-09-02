"""IDs deterministas para el interprete-serendipia (PR-0).

Contrato: MISMA (query, seed, modelo) → MISMO (activation_id, run_id).
Deriva ambos de sha256 para que la deduplicación de InterpreteStore
(PK combo_key+run_id+seed) dispare en repeticiones con misma seed,
como exige el contrato de reproducibilidad documentado en store.py.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class InterpreteIds:
    activation_id: str
    run_id: str


def interprete_ids(query: str, seed: int | None, modelo: str, repo: str = "") -> InterpreteIds:
    """Genera IDs deterministas. `seed=None` se serializa distinto de seed=0."""
    base = f"{query}|{seed!r}|{modelo}|{repo}"
    digest = hashlib.sha256(base.encode("utf-8")).hexdigest()
    return InterpreteIds(
        activation_id=f"interprete-act-{digest[:12]}",
        run_id=f"interprete-run-{digest[:12]}",
    )
