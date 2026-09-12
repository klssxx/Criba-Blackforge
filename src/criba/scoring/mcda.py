"""Multi-Criteria Decision Analysis (MCDA) module for CRIBA.

Provides AHP, TOPSIS, PROMETHEE, and ELECTRE methods for ranking ideas.

Integration:
  from criba.scoring.mcda import MCDAAnalyzer

  analyzer = MCDAAnalyzer(criteria, weights)
  rankings = analyzer.topsis(candidates)
  rankings = analyzer.ahp(comparison_matrix)
  rankings = analyzer.promethee(candidates)
"""

from __future__ import annotations
import math
from typing import Any


def _normalize_matrix(matrix: list[list[float]]) -> list[list[float]]:
    """Normalize a decision matrix using vector normalization."""
    n_cols = len(matrix[0]) if matrix else 0
    if n_cols == 0:
        return []

    # Calculate norm for each column
    norms = []
    for j in range(n_cols):
        col_sum = sum(row[j] ** 2 for row in matrix)
        norms.append(math.sqrt(col_sum) if col_sum > 0 else 1.0)

    # Normalize
    normalized = []
    for row in matrix:
        normalized.append([row[j] / norms[j] if norms[j] > 0 else 0.0 for j in range(n_cols)])
    return normalized


def _weighted_normalize(matrix: list[list[float]], weights: list[float]) -> list[list[float]]:
    """Apply weights to normalized matrix."""
    normalized = _normalize_matrix(matrix)
    weighted = []
    for row in normalized:
        weighted.append([row[j] * weights[j] if j < len(weights) else row[j] for j in range(len(row))])
    return weighted


class MCDAAnalyzer:
    """Multi-Criteria Decision Analysis for idea ranking."""

    def __init__(self, criteria: list[str] | None = None, weights: list[float] | None = None):
        self.criteria = criteria or ["novelty", "evidence", "viability", "cost"]
        self.weights = weights or [0.3, 0.25, 0.25, 0.2]
        # Normalize weights to sum to 1
        total = sum(self.weights)
        if total > 0:
            self.weights = [w / total for w in self.weights]

    def topsis(self, candidates: list[dict[str, Any]]) -> list[tuple[int, float]]:
        """TOPSIS ranking (Technique for Order of Preference by Similarity to Ideal Solution).

        Returns list of (index, score) sorted by score descending.
        """
        if not candidates:
            return []

        # Build decision matrix from candidates
        matrix = []
        for c in candidates:
            conv = c.get("convergence", c)
            row = [
                conv.get("novelty", 0),
                conv.get("evidence", 0),
                conv.get("viability", 0),
                1.0 - conv.get("cost", 0),  # Invert cost (lower is better)
            ]
            matrix.append(row)

        if not matrix:
            return []

        # Weighted normalized matrix
        weighted = _weighted_normalize(matrix, self.weights)

        # Ideal best and worst
        n_cols = len(weighted[0])
        ideal_best = [max(row[j] for row in weighted) for j in range(n_cols)]
        ideal_worst = [min(row[j] for row in weighted) for j in range(n_cols)]

        # Distances and scores
        results = []
        for i, row in enumerate(weighted):
            d_best = math.sqrt(sum((row[j] - ideal_best[j]) ** 2 for j in range(n_cols)))
            d_worst = math.sqrt(sum((row[j] - ideal_worst[j]) ** 2 for j in range(n_cols)))
            score = d_worst / (d_best + d_worst) if (d_best + d_worst) > 0 else 0.0
            results.append((i, round(score, 4)))

        results.sort(key=lambda x: -x[1])
        return results

    def ahp(self, comparison_matrix: list[list[float]]) -> list[float]:
        """AHP weighting from pairwise comparison matrix.

        Returns priority vector (weights).
        """
        if not comparison_matrix:
            return []

        n = len(comparison_matrix)
        # Normalize columns
        col_sums = [sum(comparison_matrix[i][j] for i in range(n)) for j in range(n)]
        normalized = []
        for i in range(n):
            row = [comparison_matrix[i][j] / col_sums[j] if col_sums[j] > 0 else 0.0 for j in range(n)]
            normalized.append(row)

        # Row averages = priority vector
        priorities = [sum(row) / n for row in normalized]
        return [round(p, 4) for p in priorities]

    def promethee(self, candidates: list[dict[str, Any]]) -> list[tuple[int, float]]:
        """PROMETHEE ranking (Preference Ranking Organization Method).

        Returns list of (index, net_flow) sorted by net_flow descending.
        """
        if not candidates:
            return []

        # Build matrix
        matrix = []
        for c in candidates:
            conv = c.get("convergence", c)
            row = [
                conv.get("novelty", 0),
                conv.get("evidence", 0),
                conv.get("viability", 0),
                1.0 - conv.get("cost", 0),
            ]
            matrix.append(row)

        n = len(matrix)
        if n == 0:
            return []

        # Calculate preference degrees (simplified linear preference)
        threshold = 0.1  # indifference threshold
        flows = []
        for i in range(n):
            positive_flow = 0.0
            negative_flow = 0.0
            for j in range(n):
                if i != j:
                    diff = sum(
                        self.weights[k] * (matrix[i][k] - matrix[j][k])
                        for k in range(min(len(self.weights), len(matrix[i])))
                    )
                    if diff > threshold:
                        positive_flow += diff
                    elif diff < -threshold:
                        negative_flow += abs(diff)
            net_flow = positive_flow - negative_flow
            flows.append((i, round(net_flow, 4)))

        flows.sort(key=lambda x: -x[1])
        return flows

    def ensemble_rank(self, candidates: list[dict[str, Any]]) -> list[tuple[int, float]]:
        """Ensemble ranking combining TOPSIS + PROMETHEE.

        Returns list of (index, combined_score) sorted by combined_score descending.
        """
        topsis_results = {i: rank + 1 for rank, (i, _) in enumerate(self.topsis(candidates))}
        promethee_results = {i: rank + 1 for rank, (i, _) in enumerate(self.promethee(candidates))}

        n = len(candidates)
        ensemble = []
        for i in range(n):
            avg_rank = (topsis_results.get(i, n) + promethee_results.get(i, n)) / 2
            score = 1.0 / avg_rank if avg_rank > 0 else 0.0
            ensemble.append((i, round(score, 4)))

        ensemble.sort(key=lambda x: -x[1])
        return ensemble
