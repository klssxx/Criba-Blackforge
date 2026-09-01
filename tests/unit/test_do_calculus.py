"""Unit tests for Causal DAG & Do-Calculus Engine."""
from __future__ import annotations

import pytest
from criba.core.do_calculus import CausalDAG


def test_causal_dag_creation_and_traversal() -> None:
    dag = CausalDAG()
    dag.add_node("PerimeterFirewall", is_invariant=False, current_value="static_rules")
    dag.add_node("AuthService", is_invariant=False, current_value="bearer_token")
    dag.add_node("MemorySafety", is_invariant=True, current_value="safe")

    dag.add_edge("PerimeterFirewall", "AuthService")
    dag.add_edge("AuthService", "MemorySafety")

    assert len(dag.nodes) == 3
    assert len(dag.edges) == 2


def test_do_intervention_executes_graph_surgery() -> None:
    dag = CausalDAG()
    dag.add_node("NetworkIngress")
    dag.add_node("PerimeterFirewall")
    dag.add_node("AuthService")
    dag.add_node("ProcessMemory", is_invariant=True)

    dag.add_edge("NetworkIngress", "PerimeterFirewall")
    dag.add_edge("PerimeterFirewall", "AuthService")
    dag.add_edge("AuthService", "ProcessMemory")

    # Perform do(PerimeterFirewall = "dynamic_causal_barrier")
    res = dag.do_intervention("PerimeterFirewall", "dynamic_causal_barrier")

    assert res.intervention_node == "PerimeterFirewall"
    assert ("NetworkIngress", "PerimeterFirewall") in res.graph_surgery_edges_removed
    assert "AuthService" in res.downstream_impacted_nodes
    assert "ProcessMemory" in res.downstream_impacted_nodes
    assert res.invariants_preserved is True
    assert res.counterfactual_score > 0.8
