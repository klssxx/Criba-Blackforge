"""BlackForge Orthogonal — Capa de clasificación estructural.

Módulos:
    axes.py        — 12 ejes ortogonales (catálogo inmutable)
    signature.py   — OrthogonalSignature con Jaccard correcto sobre pares
    compositor.py  — 11 modos de exploración con seed reproducible
    redundancy.py  — 4 niveles de antirredundancia
    genealogy.py   — Grafo genealógico de ideas
"""
from .axes import AXES, Axis, all_axes, get_axis, get_axis_by_name, total_cells, validate_coordinate
from .signature import OrthogonalSignature
from .compositor import CompositionMode, CompositionRequest, OrthogonalComposer, Composition
from .redundancy import RedundancyChecker, RedundancyDecision, RedundancyLevel, RedundancyResult
from .genealogy import GenealogyGraph, IdeaNode

__all__ = [
    "AXES",
    "Axis",
    "all_axes",
    "get_axis",
    "get_axis_by_name",
    "total_cells",
    "validate_coordinate",
    "OrthogonalSignature",
    "CompositionMode",
    "CompositionRequest",
    "OrthogonalComposer",
    "Composition",
    "RedundancyChecker",
    "RedundancyDecision",
    "RedundancyLevel",
    "RedundancyResult",
    "GenealogyGraph",
    "IdeaNode",
]
