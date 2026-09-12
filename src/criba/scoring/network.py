"""Network analysis module for BLACKFORGE.

Provides graph-based analysis of ideas: centrality, communities, diffusion,
and relationship mapping.

Integration:
  from criba.scoring.network import IdeaNetwork

  network = IdeaNetwork()
  for idea in ideas:
    network.add_idea(idea)
  centrality = network.centrality_scores()
  communities = network.detect_communities()
"""

from __future__ import annotations
import math
from typing import Any


class IdeaNode:
    """A node representing an idea in the network."""

    def __init__(self, idea_id: str, family: str, score: float, tags: list[str] | None = None):
        self.id = idea_id
        self.family = family
        self.score = score
        self.tags = tags or []

    def __repr__(self):
        return f"IdeaNode({self.id}, {self.family}, {self.score})"

    def __eq__(self, other):
        return isinstance(other, IdeaNode) and self.id == other.id

    def __hash__(self):
        return hash(self.id)


class IdeaEdge:
    """An edge representing a relationship between two ideas."""

    def __init__(self, source: str, target: str, weight: float = 1.0, relationship: str = "related"):
        self.source = source
        self.target = target
        self.weight = weight
        self.relationship = relationship  # "related", "similar", "derived", "conflicts"


class IdeaNetwork:
    """Graph of ideas with network analysis capabilities."""

    def __init__(self):
        self.nodes: dict[str, IdeaNode] = {}
        self.edges: list[IdeaEdge] = []

    def add_idea(self, idea_id: str, family: str, score: float, tags: list[str] | None = None):
        """Add an idea node to the network."""
        if idea_id not in self.nodes:
            self.nodes[idea_id] = IdeaNode(idea_id, family, score, tags)

    def add_edge(self, source: str, target: str, weight: float = 1.0, relationship: str = "related"):
        """Add a relationship edge between two ideas."""
        if source in self.nodes and target in self.nodes:
            self.edges.append(IdeaEdge(source, target, weight, relationship))

    def build_from_ideas(self, ideas: list[dict[str, Any]]):
        """Build network from a list of CRIBA ideas."""
        for idea in ideas:
            idea_id = idea.get("id", "")
            family = idea.get("family", "")
            conv = idea.get("convergence", {})
            score = conv.get("value_score", 0)
            tags = idea.get("tags", [])
            self.add_idea(idea_id, family, score, tags)

        # Build edges based on shared families and tags
        idea_list = list(self.nodes.values())
        for i, idea_a in enumerate(idea_list):
            for idea_b in idea_list[i + 1:]:
                weight = self._calculate_similarity(idea_a, idea_b)
                if weight > 0.3:
                    self.add_edge(idea_a.id, idea_b.id, weight)

    def _calculate_similarity(self, a: IdeaNode, b: IdeaNode) -> float:
        """Calculate similarity between two ideas [0, 1]."""
        weight = 0.0

        # Same family
        if a.family == b.family:
            weight += 0.5

        # Shared tags
        if a.tags and b.tags:
            shared = set(a.tags) & set(b.tags)
            total = set(a.tags) | set(b.tags)
            if total:
                weight += 0.3 * (len(shared) / len(total))

        # Score proximity
        if a.score > 0 and b.score > 0:
            score_diff = abs(a.score - b.score)
            weight += 0.2 * max(0, 1.0 - score_diff)

        return round(min(1.0, weight), 4)

    def centrality_scores(self) -> dict[str, float]:
        """Calculate degree centrality for each node."""
        centrality = {node_id: 0.0 for node_id in self.nodes}
        for edge in self.edges:
            centrality[edge.source] = centrality.get(edge.source, 0) + edge.weight
            centrality[edge.target] = centrality.get(edge.target, 0) + edge.weight

        # Normalize
        max_cent = max(centrality.values()) if centrality else 1
        if max_cent > 0:
            centrality = {k: round(v / max_cent, 4) for k, v in centrality.items()}
        return centrality

    def detect_communities(self) -> dict[str, int]:
        """Simple community detection based on family grouping."""
        communities = {}
        community_id = 0
        for node_id, node in self.nodes.items():
            family = node.family
            if family not in communities:
                communities[family] = community_id
                community_id += 1
        return communities

    def get_top_ideas(self, n: int = 10) -> list[tuple[str, float]]:
        """Get top N ideas by combined score (centrality + value_score)."""
        centrality = self.centrality_scores()
        scores = []
        for node_id, node in self.nodes.items():
            combined = 0.6 * node.score + 0.4 * centrality.get(node_id, 0)
            scores.append((node_id, round(combined, 4)))
        scores.sort(key=lambda x: -x[1])
        return scores[:n]

    def summary(self) -> dict[str, Any]:
        return {
            "n_ideas": len(self.nodes),
            "n_relationships": len(self.edges),
            "top_central": sorted(self.centrality_scores().items(), key=lambda x: -x[1])[:5],
            "top_combined": self.get_top_ideas(5),
            "n_families": len(set(n.family for n in self.nodes.values())),
        }
