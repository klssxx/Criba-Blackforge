"""Firma estructural ortogonal de una idea.

Una idea se representa como un conjunto de pares (axis_id, valor).
La similitud entre dos firmas se calcula con Jaccard sobre estos pares,
no sobre strings concatenados (que era el bug de la versión anterior).

Ejemplo:
    firma_a = {("AX-01", "INVERTIR"), ("AX-02", "OBJETIVO"), ("AX-11", "CONTRAFACTUAL")}
    firma_b = {("AX-01", "INVERTIR"), ("AX-02", "REGLA"), ("AX-11", "CONTRAFACTUAL")}
    sim(firma_a, firma_b) = 2/4 = 0.5
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Set, Tuple

from .axes import AXES, validate_coordinate


@dataclass(frozen=True)
class OrthogonalSignature:
    """Firma estructural de una idea en el espacio ortogonal 12-dimensional.

    Internamente es un frozenset de pares (axis_id, valor) que permite
    comparación O(1) y Jaccard correcto.
    """
    _pairs: FrozenSet[Tuple[str, str]] = field(default_factory=frozenset)

    def __init__(self, coordinates: Dict[str, Tuple[str, ...]] | None = None):
        """Construye una firma desde un diccionario {axis_id: (valores, ...)}.

        Valida que cada valor pertenezca al eje correspondiente.
        Los valores inválidos se ignoran (no rompen la construcción).
        """
        pairs: Set[Tuple[str, str]] = set()
        if coordinates:
            for axis_id, values in coordinates.items():
                if axis_id not in AXES:
                    continue
                for value in values:
                    if validate_coordinate(axis_id, value):
                        pairs.add((axis_id, value))
        object.__setattr__(self, '_pairs', frozenset(pairs))

    @property
    def pairs(self) -> FrozenSet[Tuple[str, str]]:
        """Pares (axis_id, valor) que componen la firma."""
        return self._pairs

    @property
    def coordinates(self) -> Dict[str, Tuple[str, ...]]:
        """Reconstruye el diccionario de coordenadas."""
        result: Dict[str, Set[str]] = {}
        for axis_id, value in self._pairs:
            result.setdefault(axis_id, set()).add(value)
        return {k: tuple(sorted(v)) for k, v in result.items()}

    def to_string(self) -> str:
        """Serialización canónica para comparación y hashing.

        Formato: AX01:INVERTIR|AX02:OBJETIVO|AX11:CONTRAFACTUAL
        Ordenada por (axis_id, valor) para consistencia.
        """
        return "|".join(
            f"{ax}:{val}" for ax, val in sorted(self._pairs)
        )

    def to_hash(self) -> str:
        """Hash SHA-256 de la firma para deduplicación rápida."""
        return hashlib.sha256(self.to_string().encode()).hexdigest()

    def similarity(self, other: 'OrthogonalSignature') -> float:
        """Jaccard sobre pares (axis_id, valor).

        sim(A, B) = |A ∩ B| / |A ∪ B|

        Donde A y B son conjuntos de pares (axis_id, valor).
        Esto es correcto: dos firmas son similares si comparten
        los mismos valores en los mismos ejes, no si comparten
        substrings accidentales.
        """
        if not self._pairs and not other._pairs:
            return 1.0
        if not self._pairs or not other._pairs:
            return 0.0
        intersection = len(self._pairs & other._pairs)
        union = len(self._pairs | other._pairs)
        return intersection / union if union > 0 else 0.0

    def axes_covered(self) -> Set[str]:
        """Conjunto de IDs de eje cubiertos por esta firma."""
        return {ax for ax, _ in self._pairs}

    def values_for_axis(self, axis_id: str) -> Tuple[str, ...]:
        """Valores de un eje dado en esta firma."""
        return tuple(sorted(val for ax, val in self._pairs if ax == axis_id))

    def __len__(self) -> int:
        return len(self._pairs)

    def __bool__(self) -> bool:
        return bool(self._pairs)

    def __str__(self) -> str:
        return self.to_string()

    def __hash__(self) -> int:
        return hash(self._pairs)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, OrthogonalSignature):
            return NotImplemented
        return self._pairs == other._pairs
