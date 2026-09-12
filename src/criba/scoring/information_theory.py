"""Módulo de scoring basado en teoría de la información.

Proporciona funciones de scoring que complementan al value_score clásico
con métricas de entropía, divergencia KL, información mutua y ganancia
de información.

Integración con CRIBA:
  from criba.scoring.information_theory import InformationTheoryScorer

  scorer = InformationTheoryScorer()
  info_scores = scorer.score_batch(candidates, reference_distribution)
"""

from __future__ import annotations
import math
from typing import Any


def entropy(probs: list[float]) -> float:
    """Calcular entropía de Shannon H(X) = -Σ p(x) * log2(p(x))."""
    h = 0.0
    for p in probs:
        if p > 0:
            h -= p * math.log2(p)
    return round(h, 4)


def kl_divergence(p: list[float], q: list[float]) -> float:
    """Calcular divergencia KL D(P||Q) = Σ p(x) * log2(p(x)/q(x)).

    Mide cuánta información se pierde al usar Q para aproximar P.
    """
    kl = 0.0
    for pi, qi in zip(p, q):
        if pi > 0 and qi > 0:
            kl += pi * math.log2(pi / qi)
        elif pi > 0:
            return float('inf')
    return round(kl, 4)


def mutual_information(joint: list[list[float]], marginal_x: list[float], marginal_y: list[float]) -> float:
    """Calcular información mutua I(X;Y) = ΣΣ p(x,y) * log2(p(x,y) / (p(x)*p(y)))."""
    mi = 0.0
    for i, row in enumerate(joint):
        for j, pxy in enumerate(row):
            if pxy > 0 and marginal_x[i] > 0 and marginal_y[j] > 0:
                mi += pxy * math.log2(pxy / (marginal_x[i] * marginal_y[j]))
    return round(mi, 4)


def information_gain(prior: list[float], posterior: list[float]) -> float:
    """Calcular ganancia de información IG = H(prior) - H(posterior)."""
    return round(entropy(prior) - entropy(posterior), 4)


def normalize_to_probs(values: list[float]) -> list[float]:
    """Normalizar valores a distribución de probabilidad."""
    total = sum(values)
    if total == 0:
        n = len(values)
        return [1.0 / n] * n if n > 0 else []
    return [v / total for v in values]


class InformationTheoryScorer:
    """Scorer basado en teoría de la información para CRIBA/BLACKFORGE."""

    def score_novelty(self, candidate_probs: list[float], reference_probs: list[float]) -> float:
        """Score de novedad basado en divergencia KL.

        Alto KL = candidato muy diferente de la referencia = más novedoso.
        """
        return kl_divergence(candidate_probs, reference_probs)

    def score_relevance(self, candidate_probs: list[float], reference_probs: list[float]) -> float:
        """Score de relevancia basado en similitud (1 - KL normalizada)."""
        kl = kl_divergence(candidate_probs, reference_probs)
        if kl == float('inf'):
            return 0.0
        max_kl = math.log2(len(candidate_probs))
        return round(1.0 - (kl / max_kl) if max_kl > 0 else 0.0, 4)

    def score_diversity(self, distributions: list[list[float]]) -> float:
        """Score de diversidad de un conjunto de candidatos.

        Usa entropía promedio de las distribuciones.
        Alto = candidatos diversos entre sí.
        """
        if not distributions:
            return 0.0
        entropies = [entropy(d) for d in distributions]
        return round(sum(entropies) / len(entropies), 4)

    def score_information_gain(self, prior: list[float], posterior: list[float]) -> float:
        """Score de ganancia de información.

        Cuánta información nueva aporta el posterior vs el prior.
        Alto = el candidato aporta información significativa.
        """
        return information_gain(prior, posterior)

    def score_surprise(self, probs: list[float], observed_idx: int) -> float:
        """Score de sorpresa: -log2(p(observed)).

        Alto = el candidato era poco probable = más sorprendente.
        """
        if observed_idx < 0 or observed_idx >= len(probs):
            return 0.0
        p = probs[observed_idx]
        if p <= 0:
            return float('inf')
        return round(-math.log2(p), 4)

    def score_batch(
        self,
        candidates: list[dict[str, Any]],
        reference: dict[str, Any] | None = None,
    ) -> list[dict[str, float]]:
        """Puntuar un batch de candidatos con métricas de información.

        Args:
            candidates: lista de dicts con 'probs' (distribución) y opcionalmente 'observed'
            reference: dict de referencia con 'probs'

        Returns:
            lista de dicts con 'novelty', 'relevance', 'surprise', 'info_gain'
        """
        results = []
        ref_probs = reference.get('probs', []) if reference else []

        for cand in candidates:
            cand_probs = cand.get('probs', [])
            if not cand_probs:
                results.append({'novelty': 0, 'relevance': 0, 'surprise': 0, 'info_gain': 0})
                continue

            cand_probs = normalize_to_probs(cand_probs)
            ref_probs_n = (
                normalize_to_probs(ref_probs)
                if ref_probs
                else [1.0 / len(cand_probs)] * len(cand_probs)
            )

            novelty = self.score_novelty(cand_probs, ref_probs_n)
            relevance = self.score_relevance(cand_probs, ref_probs_n)
            surprise = self.score_surprise(cand_probs, cand.get('observed', 0))
            info_gain = self.score_information_gain(ref_probs_n, cand_probs)

            results.append(
                {
                    'novelty': novelty,
                    'relevance': relevance,
                    'surprise': surprise,
                    'info_gain': info_gain,
                }
            )

        return results
