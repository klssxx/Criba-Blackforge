"""Genealogía de ideas — Grafo de relaciones padre-hijo.

Permite rastrear padres, operaciones y origen de cada idea.
Las ideas hijas se generan aplicando operaciones a las ideas padres.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class IdeaNode:
    """Nodo en el grafo genealógico."""
    technique_id: str
    parents: List[str]
    children: List[str] = field(default_factory=list)
    operations: List[str] = field(default_factory=list)
    generation: int = 0


class GenealogyGraph:
    """Grafo genealógico de ideas.

    Uso:
        graph = GenealogyGraph()
        graph.add_technique("IDEA_001", parents=[], operations=["inversion"])
        graph.add_technique("IDEA_002", parents=["IDEA_001"], operations=["recombinacion"])
        ancestors = graph.get_ancestors("IDEA_002")
        descendants = graph.get_descendants("IDEA_001")
    """

    def __init__(self):
        self.nodes: Dict[str, IdeaNode] = {}

    def add_technique(
        self,
        technique_id: str,
        parents: Optional[List[str]] = None,
        operations: Optional[List[str]] = None,
    ) -> None:
        """Añade una técnica al grafo."""
        if technique_id in self.nodes:
            return

        # Calcular generación basada en padres
        generation = 0
        if parents:
            for parent_id in parents:
                if parent_id in self.nodes:
                    generation = max(generation, self.nodes[parent_id].generation + 1)

        node = IdeaNode(
            technique_id=technique_id,
            parents=parents or [],
            operations=operations or [],
            generation=generation,
        )
        self.nodes[technique_id] = node

        # Actualizar hijos de los padres
        for parent_id in parents or []:
            if parent_id in self.nodes:
                if technique_id not in self.nodes[parent_id].children:
                    self.nodes[parent_id].children.append(technique_id)

    def add_relationship(
        self,
        parent_id: str,
        child_id: str,
        operations: Optional[List[str]] = None,
    ) -> None:
        """Añade relacion padre-hijo con operaciones."""
        if parent_id not in self.nodes:
            raise ValueError(f"Parent {parent_id} no existe en el grafo")
        if child_id not in self.nodes:
            raise ValueError(f"Child {child_id} no existe en el grafo")

        parent_node = self.nodes[parent_id]
        child_node = self.nodes[child_id]

        if child_id not in parent_node.children:
            parent_node.children.append(child_id)

        if parent_id not in child_node.parents:
            child_node.parents.append(parent_id)
            child_node.generation = max(child_node.generation, parent_node.generation + 1)

        if operations:
            for op in operations:
                if op not in child_node.operations:
                    child_node.operations.append(op)

    def get_ancestors(self, technique_id: str, max_depth: int = -1) -> List[str]:
        """Obtiene todos los ancestros de una técnica."""
        if technique_id not in self.nodes:
            return []

        ancestors: List[str] = []
        visited: Set[str] = set()
        queue: List[tuple[str, int]] = [(technique_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)

            if current_id in visited:
                continue

            visited.add(current_id)

            if current_id != technique_id:
                ancestors.append(current_id)

            if max_depth != -1 and depth >= max_depth:
                continue

            node = self.nodes.get(current_id)
            if node:
                for parent_id in node.parents:
                    if parent_id not in visited:
                        queue.append((parent_id, depth + 1))

        return ancestors

    def get_descendants(self, technique_id: str, max_depth: int = -1) -> List[str]:
        """Obtiene todos los descendientes de una técnica."""
        if technique_id not in self.nodes:
            return []

        descendants: List[str] = []
        visited: Set[str] = set()
        queue: List[tuple[str, int]] = [(technique_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)

            if current_id in visited:
                continue

            visited.add(current_id)

            if current_id != technique_id:
                descendants.append(current_id)

            if max_depth != -1 and depth >= max_depth:
                continue

            node = self.nodes.get(current_id)
            if node:
                for child_id in node.children:
                    if child_id not in visited:
                        queue.append((child_id, depth + 1))

        return descendants

    def get_lineage(self, technique_id: str) -> Dict:
        """Obtiene linaje completo (ancestros + descendientes)."""
        node = self.nodes.get(technique_id)
        return {
            "technique_id": technique_id,
            "ancestors": self.get_ancestors(technique_id),
            "descendants": self.get_descendants(technique_id),
            "generation": node.generation if node else 0,
        }

    def get_generation(self, technique_id: str) -> int:
        """Obtiene la generación de una técnica."""
        node = self.nodes.get(technique_id)
        return node.generation if node else 0

    def get_parents(self, technique_id: str) -> List[str]:
        """Obtiene los padres directos de una técnica."""
        node = self.nodes.get(technique_id)
        return node.parents if node else []

    def get_children(self, technique_id: str) -> List[str]:
        """Obtiene los hijos directos de una técnica."""
        node = self.nodes.get(technique_id)
        return node.children if node else []

    def __len__(self) -> int:
        return len(self.nodes)

    def __contains__(self, technique_id: str) -> bool:
        return technique_id in self.nodes
