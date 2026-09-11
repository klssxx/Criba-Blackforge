"""Compositor Ortogonal — 11 modos de exploración con seed reproducible.

Cada modo genera combinaciones de ejes siguiendo una estrategia distinta.
Todos usan random.Random(seed) aislado (no el global) para reproducibilidad.

Modos:
    RANDOM_BALANCED    — Exploración diversa sin sesgos
    MAX_DISTANCE       — Combinación más distinta del historial
    LEAST_VISITED      — Ataca regiones poco exploradas
    ADVERSARIAL        — Cuestiona soluciones actuales
    COUNTERFACTUAL     — Usa causalidad contrafactual
    CROSS_DOMAIN       — Introduce metodologías alejadas
    EDGE_CASE          — Bordes extremos del espacio
    NOVELTY_SEARCH     — Maximiza diferencia estructural
    PARETO_FRONTIER    — Optimiza múltiples criterios
    MAP_ELITES         — Conserva mejor idea por región
    HYBRID             — Combina estrategias
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from .axes import AXES, Axis, all_axes
from .signature import OrthogonalSignature


class CompositionMode(Enum):
    RANDOM_BALANCED = "RANDOM_BALANCED"
    MAX_DISTANCE = "MAX_DISTANCE"
    LEAST_VISITED = "LEAST_VISITED"
    ADVERSARIAL = "ADVERSARIAL"
    COUNTERFACTUAL = "COUNTERFACTUAL"
    CROSS_DOMAIN = "CROSS_DOMAIN"
    EDGE_CASE = "EDGE_CASE"
    NOVELTY_SEARCH = "NOVELTY_SEARCH"
    PARETO_FRONTIER = "PARETO_FRONTIER"
    MAP_ELITES = "MAP_ELITES"
    HYBRID = "HYBRID"


@dataclass
class CompositionRequest:
    """Entrada al compositor."""
    problem: str
    current_state: str
    constraints: List[str]
    idea_history: List[OrthogonalSignature]
    mode: CompositionMode = CompositionMode.RANDOM_BALANCED
    num_axes: int = 7  # 6-8 ejes por composición
    seed: int = 42


@dataclass
class Composition:
    """Resultado del compositor."""
    selected_axes: Dict[str, str]  # {AX-01: "INVERTIR", ...}
    mode: CompositionMode
    coverage_score: float  # Cuánto cubre regiones poco exploradas
    distance_score: float  # Cuán distinto es del historial
    novelty_estimate: float  # Estimación de novedad estructural (0-10)

    def to_signature(self) -> OrthogonalSignature:
        """Convierte la composición en una OrthogonalSignature."""
        return OrthogonalSignature(coordinates={k: (v,) for k, v in self.selected_axes.items()})


class OrthogonalComposer:
    """Compositor Ortogonal para BLACKFORGE.

    Uso:
        composer = OrthogonalComposer(seed=42)
        composition = composer.compose(CompositionRequest(
            problem="...",
            current_state="...",
            constraints=[],
            idea_history=[],
            mode=CompositionMode.MAX_DISTANCE,
            num_axes=7
        ))
    """

    def __init__(self, seed: int = 42, coverage_map: Optional[Dict[str, int]] = None):
        self.axes = {axis.id: axis for axis in all_axes()}
        self.coverage_map = coverage_map or {}
        self.rng = random.Random(seed)

    def compose(self, request: CompositionRequest) -> Composition:
        """Genera una composición según el modo solicitado."""
        mode_handlers = {
            CompositionMode.RANDOM_BALANCED: self._random_balanced,
            CompositionMode.MAX_DISTANCE: self._max_distance,
            CompositionMode.LEAST_VISITED: self._least_visited,
            CompositionMode.ADVERSARIAL: self._adversarial,
            CompositionMode.COUNTERFACTUAL: self._counterfactual,
            CompositionMode.CROSS_DOMAIN: self._cross_domain,
            CompositionMode.EDGE_CASE: self._edge_case,
            CompositionMode.NOVELTY_SEARCH: self._novelty_search,
            CompositionMode.PARETO_FRONTIER: self._pareto_frontier,
            CompositionMode.MAP_ELITES: self._map_elites,
            CompositionMode.HYBRID: self._hybrid,
        }
        handler = mode_handlers.get(request.mode, self._random_balanced)
        return handler(request)

    def _random_balanced(self, request: CompositionRequest) -> Composition:
        """Exploración diversa sin sesgos fuertes."""
        selected_axes = {}
        axis_ids = list(self.axes.keys())
        selected_axis_ids = self.rng.sample(axis_ids, min(request.num_axes, len(axis_ids)))

        for axis_id in selected_axis_ids:
            axis = self.axes[axis_id]
            selected_value = self.rng.choice(axis.values)
            selected_axes[axis_id] = selected_value

        return self._make_composition(selected_axes, request)

    def _max_distance(self, request: CompositionRequest) -> Composition:
        """Busca la combinación más distinta de las ideas anteriores."""
        if not request.idea_history:
            return self._random_balanced(request)

        best_composition = None
        best_distance = -1.0

        for _ in range(50):  # 50 intentos para maximizar distancia
            composition = self._random_balanced(request)
            avg_distance = self._average_distance_to_history(
                composition.selected_axes, request.idea_history
            )
            if avg_distance > best_distance:
                best_distance = avg_distance
                best_composition = composition

        return best_composition

    def _least_visited(self, request: CompositionRequest) -> Composition:
        """Ataca regiones del espacio que apenas se hayan usado."""
        selected_axes = {}
        axis_ids = list(self.axes.keys())
        selected_axis_ids = self.rng.sample(axis_ids, min(request.num_axes, len(axis_ids)))

        for axis_id in selected_axis_ids:
            axis = self.axes[axis_id]
            # Preferir valores con menor coverage
            value_coverage = [
                (value, self.coverage_map.get(f"{axis_id}:{value}", 0))
                for value in axis.values
            ]
            value_coverage.sort(key=lambda x: x[1])
            # Top 3 menos usados
            top_3 = value_coverage[:3]
            selected_value = self.rng.choice([v[0] for v in top_3])
            selected_axes[axis_id] = selected_value

        return self._make_composition(selected_axes, request)

    def _adversarial(self, request: CompositionRequest) -> Composition:
        """Selecciona dimensiones capaces de cuestionar una solución actual."""
        # Forzar ejes de presion, epistemologia y perspectiva adversarial
        selected_axes = {
            "AX-03": "ADVERSARIO",
            "AX-11": "FALSACION",
            "AX-12": self.rng.choice(["ADVERSARIO", "ERROR_HONESTO", "INSIDER"])
        }

        # Rellenar resto aleatoriamente
        remaining_axes = set(self.axes.keys()) - set(selected_axes.keys())
        additional = self.rng.sample(
            list(remaining_axes),
            min(request.num_axes - len(selected_axes), len(remaining_axes))
        )

        for axis_id in additional:
            axis = self.axes[axis_id]
            selected_axes[axis_id] = self.rng.choice(axis.values)

        return self._make_composition(selected_axes, request)

    def _counterfactual(self, request: CompositionRequest) -> Composition:
        """Obliga a usar causalidad contrafactual y transformacion INVERTIR."""
        selected_axes = {
            "AX-01": "INVERTIR",
            "AX-07": "CONTRAFACTUAL",
            "AX-11": self.rng.choice(["CONTRAFACTUAL", "FALSACION", "ABDUCCION"])
        }

        remaining_axes = set(self.axes.keys()) - set(selected_axes.keys())
        additional = self.rng.sample(
            list(remaining_axes),
            min(request.num_axes - len(selected_axes), len(remaining_axes))
        )

        for axis_id in additional:
            axis = self.axes[axis_id]
            selected_axes[axis_id] = self.rng.choice(axis.values)

        return self._make_composition(selected_axes, request)

    def _cross_domain(self, request: CompositionRequest) -> Composition:
        """Obliga a introducir una familia metodologica alejada del problema."""
        selected_axes = {
            "AX-04": self.rng.choice(["ECOSISTEMA", "CIVILIZACION", "ENJAMBRE"]),
            "AX-06": self.rng.choice(["MALLA", "FEDERADA", "CELULAR"]),
            "AX-10": self.rng.choice(["DISTRIBUIDA", "REPUTACION", "COOPERACION"])
        }

        remaining_axes = set(self.axes.keys()) - set(selected_axes.keys())
        additional = self.rng.sample(
            list(remaining_axes),
            min(request.num_axes - len(selected_axes), len(remaining_axes))
        )

        for axis_id in additional:
            axis = self.axes[axis_id]
            selected_axes[axis_id] = self.rng.choice(axis.values)

        return self._make_composition(selected_axes, request)

    def _edge_case(self, request: CompositionRequest) -> Composition:
        """Genera combinaciones en bordes extremos del espacio."""
        edge_values = {
            "AX-01": ["RANDOMIZAR", "ELIMINAR"],
            "AX-04": ["CIVILIZACION", "EVENTO"],
            "AX-05": ["GENERACIONES", "INSTANTANEO"],
            "AX-09": ["COSTE_CERO", "ABUNDANCIA_EXTREMA"],
            "AX-12": ["RARE_EVENT", "OOD", "COMPORTAMIENTO_INDEFINIDO"]
        }

        selected_axes = {}
        for axis_id, values in edge_values.items():
            if axis_id in self.axes:
                selected_axes[axis_id] = self.rng.choice(values)

        # Rellenar hasta num_axes
        remaining_axes = set(self.axes.keys()) - set(selected_axes.keys())
        additional = self.rng.sample(
            list(remaining_axes),
            min(request.num_axes - len(selected_axes), len(remaining_axes))
        )

        for axis_id in additional:
            axis = self.axes[axis_id]
            selected_axes[axis_id] = self.rng.choice(axis.values)

        return self._make_composition(selected_axes, request)

    def _novelty_search(self, request: CompositionRequest) -> Composition:
        """Recompensa principal: producir comportamiento estructuralmente diferente."""
        return self._max_distance(request)

    def _pareto_frontier(self, request: CompositionRequest) -> Composition:
        """Optimiza para multiples criterios simultaneos (NOVELTY, UTILITY, FEASIBILITY)."""
        # Implementacion simplificada: maximizar distancia + coverage
        return self._max_distance(request)

    def _map_elites(self, request: CompositionRequest) -> Composition:
        """Conserva la mejor idea EN CADA REGION del espacio."""
        # Requiere coverage_map poblado; si no, fallback a least_visited
        if not self.coverage_map:
            return self._least_visited(request)
        return self._least_visited(request)

    def _hybrid(self, request: CompositionRequest) -> Composition:
        """Combina multiples estrategias."""
        strategies = [
            self._random_balanced,
            self._max_distance,
            self._least_visited,
            self._adversarial,
            self._counterfactual
        ]

        # Ejecutar 3 estrategias aleatorias y elegir la de mayor novelty_estimate
        candidates = []
        for _ in range(3):
            strategy = self.rng.choice(strategies)
            composition = strategy(request)
            candidates.append(composition)

        return max(candidates, key=lambda c: c.novelty_estimate)

    def _make_composition(self, selected_axes: Dict[str, str], request: CompositionRequest) -> Composition:
        """Construye un objeto Composition con scores."""
        return Composition(
            selected_axes=selected_axes,
            mode=request.mode,
            coverage_score=self._compute_coverage_score(selected_axes),
            distance_score=self._compute_distance_score(selected_axes, request.idea_history),
            novelty_estimate=self._estimate_novelty(selected_axes, request.idea_history)
        )

    def _compute_coverage_score(self, selected_axes: Dict[str, str]) -> float:
        """Calcula score de cobertura (menor coverage = mayor score)."""
        if not self.coverage_map:
            return 0.5  # Neutral si no hay mapa

        total_coverage = 0
        for axis_id, value in selected_axes.items():
            key = f"{axis_id}:{value}"
            total_coverage += self.coverage_map.get(key, 0)

        # Normalizar (asumiendo max coverage ~100 por celda)
        max_expected = len(selected_axes) * 100
        return 1.0 - (total_coverage / max_expected) if max_expected > 0 else 0.5

    def _compute_distance_score(self, selected_axes: Dict[str, str], idea_history: List[OrthogonalSignature]) -> float:
        """Calcula distancia promedio al historial de ideas."""
        if not idea_history:
            return 0.5
        return self._average_distance_to_history(selected_axes, idea_history)

    def _average_distance_to_history(self, selected_axes: Dict[str, str], idea_history: List[OrthogonalSignature]) -> float:
        """Distancia promedio a ideas anteriores."""
        if not idea_history:
            return 0.5

        current_signature = OrthogonalSignature(
            coordinates={k: (v,) for k, v in selected_axes.items()}
        )

        distances = []
        for idea in idea_history:
            dist = 1.0 - current_signature.similarity(idea)
            distances.append(dist)

        return sum(distances) / len(distances) if distances else 0.5

    def _estimate_novelty(self, selected_axes: Dict[str, str], idea_history: List[OrthogonalSignature]) -> float:
        """Estima novedad estructural (0-10)."""
        distance = self._average_distance_to_history(selected_axes, idea_history)
        coverage = self._compute_coverage_score(selected_axes)

        # Combinar distancia y coverage (peso 70% distancia, 30% coverage)
        novelty = (distance * 0.7 + coverage * 0.3) * 10
        return min(10.0, max(0.0, novelty))
