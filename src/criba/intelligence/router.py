"""Dynamic technique router over the T001-T130 canon (§5.D-§5.F, §6 del mandato).

Selects the minimal high-value subset of registry techniques relevant to a task.
Deterministic and offline: reads only technique_registry.yaml metadata — no
model calls, no network, no execution. Implemented techniques become execution
candidates; PLANNED ones surface only as coverage gaps, never as capability
(the absence of a ficha is never replaced by invented content).
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .registry import Technique, TechniqueRegistry

_TOKEN_SPLIT = re.compile(r"[^a-z0-9áéíóúñü]+")

# Minimal ES/EN stopword set — embedded so routing stays offline and stable.
_STOPWORDS = frozenset({
    "de", "la", "el", "los", "las", "un", "una", "unos", "unas", "y", "o",
    "que", "como", "para", "por", "con", "del", "al", "en", "es", "son",
    "the", "a", "an", "of", "to", "in", "on", "for", "with", "and", "or",
    "is", "are", "be", "how", "what", "which", "this", "that", "it", "its",
})

# Security-leaning families get extra weight under the BLACKFORGE profile.
_PROFILE_FAMILY_WEIGHTS: dict[str, dict[str, float]] = {
    "CRIBA": {},
    "BLACKFORGE": {
        "ADVERSARIAL_FUTURES": 1.25,
        "SIGNALS_EVIDENCE_OPPORTUNITY": 1.25,
    },
}

_IMPLEMENTED_PREFIX = "IMPLEMENTED"
_CREDENTIAL_EXCLUSION = -1_000.0

# Lexical bridge ES->EN over the canon vocabulary (canon metadata is English).
# Task-side normalization only: deterministic, falsable, no invented content.
_TOKEN_BRIDGE: dict[str, str] = {
    "patente": "patent", "patentes": "patent",
    "publicacion": "publication", "publicaciones": "publication",
    "cientifico": "scientific", "cientifica": "scientific",
    "tendencia": "trend", "tendencias": "trend",
    "senal": "signal", "senales": "signal",
    "evidencia": "evidence", "evidencias": "evidence",
    "oportunidad": "opportunity", "oportunidades": "opportunity",
    "adversario": "adversarial", "adversarios": "adversarial",
    "adversarial": "adversarial", "adversariales": "adversarial",
    "morfologico": "morphological", "morfologica": "morphological",
    "hipotesis": "hypothesis",
    "sustitucion": "substitution", "sustituciones": "substitution",
    "genealogia": "genealogy", "genealogias": "genealogy",
    "curva": "curve", "curvas": "curve",
    "restriccion": "constraint", "restricciones": "constraint",
    "inversion": "inversion", "inversiones": "inversion",
    "anomalia": "anomaly", "anomalias": "anomaly",
    "futuro": "future", "futuros": "future",
    "contrafactual": "counterfactual",
    "deteccion": "detection", "detectar": "detection",
    "busqueda": "search", "buscar": "search",
    "analisis": "analysis",
    "desbloqueo": "unlock",
    "cuello": "bottleneck",
}


@dataclass(frozen=True)
class CandidateTechnique:
    """A technique scored for a task, with the reasons behind its score."""

    technique: Technique
    score: float
    reasons: tuple[str, ...]
    executable: bool

    @property
    def id(self) -> str:
        return self.technique.id


@dataclass(frozen=True)
class SelectionResult:
    """Router output: execution candidates + honest coverage gaps + provenance."""

    task: str
    profile: str
    selected: tuple[CandidateTechnique, ...]
    coverage_gaps: tuple[CandidateTechnique, ...]
    canon_version: str | None
    provenance: Mapping[str, Any]
    excluded: tuple[str, ...] = field(default=())

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "profile": self.profile,
            "canon_version": self.canon_version,
            "provenance": dict(self.provenance),
            "selected": [
                {"id": c.id, "name": c.technique.name, "score": round(c.score, 4),
                 "reasons": list(c.reasons), "executable": c.executable}
                for c in self.selected
            ],
            "coverage_gaps": [
                {"id": c.id, "name": c.technique.name, "score": round(c.score, 4),
                 "reasons": list(c.reasons)}
                for c in self.coverage_gaps
            ],
            "excluded": list(self.excluded),
        }


def _normalize_token(token: str) -> str:
    """NFD accent-stripping ('análisis' -> 'analisis')."""
    decomposed = unicodedata.normalize("NFD", token)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _singularize(token: str) -> str:
    if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _tokens(text: str) -> set[str]:
    out: set[str] = set()
    for token in _TOKEN_SPLIT.split(text.lower()):
        if len(token) <= 2 or token in _STOPWORDS:
            continue
        base = _normalize_token(token)
        bridged = _TOKEN_BRIDGE.get(base)
        if bridged is None and base.endswith("s"):
            # plurales -s/-es contra el puente: 'contrafactuales'->'contrafactual'
            bridged = _TOKEN_BRIDGE.get(base[:-1]) or _TOKEN_BRIDGE.get(base[:-2])
        singular = _singularize(bridged or base)
        if len(singular) > 2:
            out.add(singular)
    return out


def _technique_tokens(t: Technique) -> dict[str, float]:
    """Weighted metadata tokens: name x3, subtechniques x2, family/pipelines x1."""
    weights: dict[str, float] = {}
    for token in _tokens(t.name):
        weights[token] = weights.get(token, 0.0) + 3.0
    for sub in t.subtechniques:
        for token in _tokens(sub):
            weights[token] = weights.get(token, 0.0) + 2.0
    for part in (t.family, *t.pipelines):
        for token in _tokens(part.replace("_", " ")):
            weights[token] = weights.get(token, 0.0) + 1.0
    return weights


def _reason_token_list(tokens: list[str], limit: int = 80) -> str:
    """Join matched tokens for a reason string without cutting one mid-token.

    Greedy: whole tokens are kept while they fit `limit`; the first token is
    always kept so a single over-long token is never manufactured into a
    non-token. Never leaves a trailing comma (qa P3-1).
    """
    parts: list[str] = []
    length = 0
    for token in tokens:
        extra = len(token) + (1 if parts else 0)
        if parts and length + extra > limit:
            break
        parts.append(token)
        length += extra
    return ",".join(parts)


class TechniqueRouter:
    """Read-only router: task text -> minimal relevant technique subset."""

    def __init__(self, registry: TechniqueRegistry):
        self._registry = registry
        self._doc_tokens: dict[str, dict[str, float]] = {
            t.id: _technique_tokens(t) for t in registry.all()
        }

    def select(
        self,
        task: str,
        profile: str = "CRIBA",
        *,
        max_techniques: int = 6,
        max_per_family: int = 2,
        offline_only: bool = True,
        adaptive: bool = False,
        outcome_store: Any | None = None,
        prior_weight: float = 1.0,
    ) -> SelectionResult:
        """Selecciona el subconjunto mínimo relevante.

        ``adaptive=False`` (default) es byte-idéntico al comportamiento
        congelado: prior empírico desactivado, invariante "misma seed = mismo
        output" intacto. ``adaptive=True`` es opt-in: suma un prior UCB del
        ``outcome_store`` al score léxico SOLO de candidatos ya elegibles —
        NUNCA convierte una PLANNED en ejecutable (el canon decide eso).
        """
        if profile not in _PROFILE_FAMILY_WEIGHTS:
            raise ValueError(f"unknown profile: {profile}")
        # 0/negative limits are caller bugs, not empty queries: an empty
        # selection must stay reachable only through a task with no real
        # overlap, never through an invalid limit silently collapsing to ()
        # (qa P3-2).
        if max_techniques < 1:
            raise ValueError(f"max_techniques must be >= 1, got {max_techniques}")
        if max_per_family < 1:
            raise ValueError(f"max_per_family must be >= 1, got {max_per_family}")
        task_tokens = _tokens(task)
        family_weights = _PROFILE_FAMILY_WEIGHTS[profile]

        scored: list[CandidateTechnique] = []
        excluded: list[str] = []
        for technique in self._registry.all():
            doc = self._doc_tokens[technique.id]
            overlap = sum(w for token, w in doc.items() if token in task_tokens)
            if overlap <= 0.0:
                continue  # sin coincidencia real: no se selecciona ni se inventa relevancia
            reasons = [f"coincide:{_reason_token_list(sorted(set(doc) & task_tokens))}"]
            if technique.requires_credentials:
                excluded.append(f"{technique.id}:requiere_credenciales")
                continue
            if offline_only and technique.requires_network:
                excluded.append(f"{technique.id}:requiere_red_offline_only")
                continue
            executable = technique.status.startswith(_IMPLEMENTED_PREFIX)
            score = overlap
            if executable:
                score += 2.0
                reasons.append(f"implementada:{technique.status}")
            else:
                reasons.append(f"no_implementada:{technique.status}")
            if technique.requires_network:
                score -= 0.5
                reasons.append("penalizacion:red")
            if technique.family in family_weights:
                score *= family_weights[technique.family]
                reasons.append(f"perfil:{profile}:{technique.family}")
            # Prior empírico (opt-in): solo reordena elegibles, nunca promociona
            # una PLANNED a ejecutable. Se audita en `reasons` (§13.8).
            if adaptive and outcome_store is not None:
                prior, n_eff, label = outcome_store.prior(
                    profile=profile,
                    family=technique.family,
                    technique_id=technique.id,
                    canon_version=self._registry.canon_version,
                )
                if n_eff > 0:
                    score += prior_weight * prior
                    reasons.append(f"prior:{label}")
            scored.append(CandidateTechnique(technique, score, tuple(reasons), executable))

        selected, gaps = self._diverse_top(
            scored, max_techniques=max_techniques, max_per_family=max_per_family,
        )
        return SelectionResult(
            task=task,
            profile=profile,
            selected=tuple(selected),
            coverage_gaps=tuple(gaps),
            canon_version=self._registry.canon_version,
            provenance=self._registry.provenance,
            excluded=tuple(excluded),
        )

    def _diverse_top(
        self,
        scored: list[CandidateTechnique],
        *,
        max_techniques: int,
        max_per_family: int,
    ) -> tuple[list[CandidateTechnique], list[CandidateTechnique]]:
        """Greedy pick with functional diversity and redundancy suppression."""
        ordered = sorted(scored, key=lambda c: (-c.score, c.id))
        family_count: Counter[str] = Counter()
        seen_modules: dict[str, set[str]] = {}
        selected: list[CandidateTechnique] = []
        gaps: list[CandidateTechnique] = []
        for candidate in ordered:
            technique = candidate.technique
            if family_count[technique.family] >= max_per_family:
                continue  # saturada: otra familia aporta más diversidad funcional
            module_key = technique.module[0] if technique.module else technique.id
            pipeline_key = ",".join(technique.pipelines)
            if pipeline_key in seen_modules.get(module_key, set()):
                continue  # redundante: mismo módulo y mismo pipeline que ya está en el equipo
            family_count[technique.family] += 1
            seen_modules.setdefault(module_key, set()).add(pipeline_key)
            if candidate.executable:
                if len(selected) >= max_techniques:
                    continue
                selected.append(candidate)
            else:
                if len(gaps) >= max_techniques:
                    continue
                gaps.append(candidate)
        return selected, gaps
