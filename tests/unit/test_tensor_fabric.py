"""Unit tests for Hyper-Dimensional Causal Tensor Fabric."""
from __future__ import annotations

from criba.core.tensor_fabric import TensorFabric


def test_tensor_fabric_loads_and_vectorizes() -> None:
    fabric = TensorFabric()
    assert len(fabric.records) > 0
    assert len(fabric.vectors) == len(fabric.records)
    assert len(fabric.vectors[0]) >= 15


def test_orthogonality_matrix_computation() -> None:
    fabric = TensorFabric()
    sample_ids = [fabric.records[0]["blackforge_id"], fabric.records[1]["blackforge_id"]]
    matrix = fabric.compute_orthogonality_matrix(sample_ids)
    
    assert len(matrix) == 2
    assert len(matrix[0]) == 2
    # Self distance is ~0.0
    assert matrix[0][0] <= 0.001


def test_find_orthogonal_frontier_filters_adjacent_possible() -> None:
    fabric = TensorFabric()
    frontier = fabric.find_orthogonal_frontier(
        query="Fortalecer la defensa de memoria en microservicios",
        top_k=6,
        min_distance=0.45,
        max_distance=0.85
    )
    
    for item in frontier:
        dist = item["adjacent_possible_distance"]
        assert 0.45 <= dist <= 0.85
        assert "orthogonal_entropy" in item
