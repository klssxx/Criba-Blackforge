"""Tests para BlackForge Orthogonal."""
import pytest

from criba.blackforge_orthogonal.axes import (
    AXES,
    Axis,
    all_axes,
    get_axis,
    get_axis_by_name,
    total_cells,
    validate_coordinate,
)
from criba.blackforge_orthogonal.signature import OrthogonalSignature
from criba.blackforge_orthogonal.compositor import (
    CompositionMode,
    CompositionRequest,
    OrthogonalComposer,
)
from criba.blackforge_orthogonal.redundancy import (
    RedundancyChecker,
    RedundancyDecision,
    RedundancyLevel,
)
from criba.blackforge_orthogonal.genealogy import GenealogyGraph


# ══════════════════════════════════════════════════════════════════════
# AXES
# ══════════════════════════════════════════════════════════════════════

class TestAxes:
    def test_12_axes_exist(self):
        assert len(AXES) == 12

    def test_axis_ids(self):
        expected = {f"AX-{i:02d}" for i in range(1, 13)}
        assert set(AXES.keys()) == expected

    def test_all_axes_in_order(self):
        axes = all_axes()
        assert len(axes) == 12
        assert axes[0].id == "AX-01"
        assert axes[-1].id == "AX-12"

    def test_get_axis(self):
        ax = get_axis("AX-01")
        assert ax is not None
        assert ax.name == "TRANSFORMACION"

    def test_get_axis_invalid(self):
        assert get_axis("AX-99") is None

    def test_get_axis_by_name(self):
        ax = get_axis_by_name("TRANSFORMACION")
        assert ax is not None
        assert ax.id == "AX-01"

    def test_validate_coordinate_valid(self):
        assert validate_coordinate("AX-01", "INVERTIR") is True

    def test_validate_coordinate_invalid_value(self):
        assert validate_coordinate("AX-01", "INVALID") is False

    def test_validate_coordinate_invalid_axis(self):
        assert validate_coordinate("AX-99", "INVERTIR") is False

    def test_total_cells(self):
        total = total_cells()
        expected = sum(len(ax.values) for ax in AXES.values())
        assert total == expected
        assert total > 100  # Hay más de 100 celdas en el espacio

    def test_axis_is_frozen(self):
        ax = AXES["AX-01"]
        with pytest.raises(AttributeError):
            ax.id = "AX-99"

    def test_axis_hash(self):
        ax1 = AXES["AX-01"]
        ax2 = AXES["AX-01"]
        assert hash(ax1) == hash(ax2)
        assert ax1 == ax2


# ══════════════════════════════════════════════════════════════════════
# SIGNATURE
# ══════════════════════════════════════════════════════════════════════

class TestOrthogonalSignature:
    def test_empty_signature(self):
        sig = OrthogonalSignature()
        assert len(sig) == 0
        assert not sig

    def test_basic_construction(self):
        sig = OrthogonalSignature(coordinates={
            "AX-01": ("INVERTIR",),
            "AX-02": ("OBJETIVO",),
        })
        assert len(sig) == 2
        assert ("AX-01", "INVERTIR") in sig.pairs
        assert ("AX-02", "OBJETIVO") in sig.pairs

    def test_invalid_values_ignored(self):
        sig = OrthogonalSignature(coordinates={
            "AX-01": ("INVERTIR", "INVALID"),
            "AX-99": ("OBJETIVO",),  # eje no existe
        })
        assert len(sig) == 1
        assert ("AX-01", "INVERTIR") in sig.pairs

    def test_identical_signatures_similarity_1(self):
        sig_a = OrthogonalSignature(coordinates={
            "AX-01": ("INVERTIR",),
            "AX-02": ("OBJETIVO",),
        })
        sig_b = OrthogonalSignature(coordinates={
            "AX-01": ("INVERTIR",),
            "AX-02": ("OBJETIVO",),
        })
        assert sig_a.similarity(sig_b) == 1.0

    def test_different_signatures_similarity_lt_1(self):
        sig_a = OrthogonalSignature(coordinates={
            "AX-01": ("INVERTIR",),
            "AX-02": ("OBJETIVO",),
        })
        sig_b = OrthogonalSignature(coordinates={
            "AX-01": ("ELIMINAR",),
            "AX-02": ("REGLA",),
        })
        assert sig_a.similarity(sig_b) < 1.0

    def test_empty_signatures_similarity(self):
        sig_a = OrthogonalSignature()
        sig_b = OrthogonalSignature()
        assert sig_a.similarity(sig_b) == 1.0

    def test_one_empty_similarity(self):
        sig_a = OrthogonalSignature(coordinates={"AX-01": ("INVERTIR",)})
        sig_b = OrthogonalSignature()
        assert sig_a.similarity(sig_b) == 0.0

    def test_partial_overlap(self):
        sig_a = OrthogonalSignature(coordinates={
            "AX-01": ("INVERTIR",),
            "AX-02": ("OBJETIVO",),
            "AX-11": ("CONTRAFACTUAL",),
        })
        sig_b = OrthogonalSignature(coordinates={
            "AX-01": ("INVERTIR",),
            "AX-02": ("REGLA",),
            "AX-11": ("CONTRAFACTUAL",),
        })
        # 2 de 4 pares coinciden
        assert sig_a.similarity(sig_b) == 0.5

    def test_to_string(self):
        sig = OrthogonalSignature(coordinates={
            "AX-01": ("INVERTIR",),
            "AX-02": ("OBJETIVO",),
        })
        s = sig.to_string()
        assert "AX-01:INVERTIR" in s
        assert "AX-02:OBJETIVO" in s

    def test_to_hash(self):
        sig = OrthogonalSignature(coordinates={"AX-01": ("INVERTIR",)})
        h = sig.to_hash()
        assert len(h) == 64  # SHA-256 hex

    def test_axes_covered(self):
        sig = OrthogonalSignature(coordinates={
            "AX-01": ("INVERTIR", "ELIMINAR"),
            "AX-02": ("OBJETIVO",),
        })
        assert sig.axes_covered() == {"AX-01", "AX-02"}

    def test_values_for_axis(self):
        sig = OrthogonalSignature(coordinates={
            "AX-01": ("INVERTIR", "ELIMINAR"),
        })
        vals = sig.values_for_axis("AX-01")
        assert set(vals) == {"INVERTIR", "ELIMINAR"}

    def test_coordinates_roundtrip(self):
        coords = {
            "AX-01": ("INVERTIR", "ELIMINAR"),
            "AX-02": ("OBJETIVO",),
        }
        sig = OrthogonalSignature(coordinates=coords)
        result = sig.coordinates
        assert set(result["AX-01"]) == {"INVERTIR", "ELIMINAR"}
        assert set(result["AX-02"]) == {"OBJETIVO"}


# ══════════════════════════════════════════════════════════════════════
# COMPOSER
# ══════════════════════════════════════════════════════════════════════

class TestOrthogonalComposer:
    def test_random_balanced(self):
        composer = OrthogonalComposer(seed=42)
        request = CompositionRequest(
            problem="test",
            current_state="test",
            constraints=[],
            idea_history=[],
            mode=CompositionMode.RANDOM_BALANCED,
            num_axes=7,
        )
        comp = composer.compose(request)
        assert len(comp.selected_axes) == 7
        assert comp.mode == CompositionMode.RANDOM_BALANCED

    def test_max_distance(self):
        composer = OrthogonalComposer(seed=42)
        history = [
            OrthogonalSignature(coordinates={
                "AX-01": ("INVERTIR",),
                "AX-02": ("OBJETIVO",),
            })
        ]
        request = CompositionRequest(
            problem="test",
            current_state="test",
            constraints=[],
            idea_history=history,
            mode=CompositionMode.MAX_DISTANCE,
            num_axes=7,
        )
        comp = composer.compose(request)
        assert len(comp.selected_axes) == 7
        assert comp.distance_score >= 0.0

    def test_adversarial_forces_axes(self):
        composer = OrthogonalComposer(seed=42)
        request = CompositionRequest(
            problem="test",
            current_state="test",
            constraints=[],
            idea_history=[],
            mode=CompositionMode.ADVERSARIAL,
            num_axes=7,
        )
        comp = composer.compose(request)
        assert "AX-03" in comp.selected_axes
        assert "AX-11" in comp.selected_axes
        assert "AX-12" in comp.selected_axes

    def test_counterfactual_forces_axes(self):
        composer = OrthogonalComposer(seed=42)
        request = CompositionRequest(
            problem="test",
            current_state="test",
            constraints=[],
            idea_history=[],
            mode=CompositionMode.COUNTERFACTUAL,
            num_axes=7,
        )
        comp = composer.compose(request)
        assert comp.selected_axes.get("AX-01") == "INVERTIR"
        assert comp.selected_axes.get("AX-07") == "CONTRAFACTUAL"

    def test_minimal_axes(self):
        composer = OrthogonalComposer(seed=42)
        request = CompositionRequest(
            problem="test",
            current_state="test",
            constraints=[],
            idea_history=[],
            mode=CompositionMode.RANDOM_BALANCED,
            num_axes=3,
        )
        comp = composer.compose(request)
        assert len(comp.selected_axes) == 3

    def test_reproducibility(self):
        """Mismo seed → misma composición."""
        composer1 = OrthogonalComposer(seed=42)
        composer2 = OrthogonalComposer(seed=42)
        request = CompositionRequest(
            problem="test",
            current_state="test",
            constraints=[],
            idea_history=[],
            mode=CompositionMode.RANDOM_BALANCED,
            num_axes=7,
        )
        comp1 = composer1.compose(request)
        comp2 = composer2.compose(request)
        assert comp1.selected_axes == comp2.selected_axes

    def test_no_duplicate_values_in_signature(self):
        """La composición no debe tener valores duplicados en la firma."""
        composer = OrthogonalComposer(seed=42)
        request = CompositionRequest(
            problem="test",
            current_state="test",
            constraints=[],
            idea_history=[],
            mode=CompositionMode.RANDOM_BALANCED,
            num_axes=7,
        )
        comp = composer.compose(request)
        sig = comp.to_signature()
        # No debe haber valores duplicados en un mismo eje
        for axis_id, vals in sig.coordinates.items():
            assert len(vals) == len(set(vals))

    def test_all_modes_produce_valid_composition(self):
        """Todos los modos deben producir composiciones válidas."""
        composer = OrthogonalComposer(seed=42)
        for mode in CompositionMode:
            request = CompositionRequest(
                problem="test",
                current_state="test",
                constraints=[],
                idea_history=[],
                mode=mode,
                num_axes=7,
            )
            comp = composer.compose(request)
            assert len(comp.selected_axes) > 0
            assert comp.novelty_estimate >= 0.0


# ══════════════════════════════════════════════════════════════════════
# REDUNDANCY
# ══════════════════════════════════════════════════════════════════════

class TestRedundancyChecker:
    def test_identical_texts_redundant(self):
        checker = RedundancyChecker()
        sig = OrthogonalSignature(coordinates={"AX-01": ("INVERTIR",)})
        result = checker.check(sig, sig, "texto identico", "texto identico")
        assert result.decision == RedundancyDecision.REDUNDANT

    def test_different_ideas_new(self):
        checker = RedundancyChecker()
        sig_a = OrthogonalSignature(coordinates={"AX-01": ("INVERTIR",)})
        sig_b = OrthogonalSignature(coordinates={"AX-01": ("ELIMINAR",)})
        result = checker.check(sig_a, sig_b, "texto a", "texto b")
        assert result.decision == RedundancyDecision.NEW

    def test_identical_structures_derivative(self):
        checker = RedundancyChecker()
        sig = OrthogonalSignature(coordinates={"AX-01": ("INVERTIR",)})
        result = checker.check(sig, sig, "texto a", "texto b diferente")
        assert result.decision == RedundancyDecision.DERIVATIVE

    def test_merge_candidate(self):
        checker = RedundancyChecker()
        sig_a = OrthogonalSignature(coordinates={
            "AX-01": ("INVERTIR",),
            "AX-02": ("OBJETIVO",),
        })
        sig_b = OrthogonalSignature(coordinates={
            "AX-01": ("INVERTIR",),
            "AX-02": ("OBJETIVO",),
        })
        result = checker.check(sig_a, sig_b, "texto similar", "texto similar")
        assert result.decision == RedundancyDecision.MERGE_CANDIDATE

    def test_causal_variant(self):
        checker = RedundancyChecker()
        sig_a = OrthogonalSignature(coordinates={
            "AX-01": ("INVERTIR",),
            "AX-07": ("CONTRAFACTUAL",),
            "AX-11": ("FALSACION",),
        })
        sig_b = OrthogonalSignature(coordinates={
            "AX-01": ("INVERTIR",),
            "AX-07": ("CONTRAFACTUAL",),
            "AX-11": ("FALSACION",),
        })
        result = checker.check(sig_a, sig_b, "texto a", "texto b")
        assert result.decision == RedundancyDecision.VARIANT


# ══════════════════════════════════════════════════════════════════════
# GENEALOGY
# ══════════════════════════════════════════════════════════════════════

class TestGenealogyGraph:
    def test_add_technique(self):
        graph = GenealogyGraph()
        graph.add_technique("IDEA_001")
        assert "IDEA_001" in graph

    def test_add_relationship(self):
        graph = GenealogyGraph()
        graph.add_technique("IDEA_001")
        graph.add_technique("IDEA_002", parents=["IDEA_001"])
        graph.add_relationship("IDEA_001", "IDEA_002")
        assert "IDEA_002" in graph.get_children("IDEA_001")
        assert "IDEA_001" in graph.get_parents("IDEA_002")

    def test_get_ancestors(self):
        graph = GenealogyGraph()
        graph.add_technique("A")
        graph.add_technique("B", parents=["A"])
        graph.add_technique("C", parents=["B"])
        ancestors = graph.get_ancestors("C")
        assert "A" in ancestors
        assert "B" in ancestors

    def test_get_descendants(self):
        graph = GenealogyGraph()
        graph.add_technique("A")
        graph.add_technique("B", parents=["A"])
        graph.add_technique("C", parents=["B"])
        descendants = graph.get_descendants("A")
        assert "B" in descendants
        assert "C" in descendants

    def test_get_lineage(self):
        graph = GenealogyGraph()
        graph.add_technique("A")
        graph.add_technique("B", parents=["A"])
        lineage = graph.get_lineage("B")
        assert lineage["ancestors"] == ["A"]
        assert lineage["descendants"] == []

    def test_generation(self):
        graph = GenealogyGraph()
        graph.add_technique("A")
        graph.add_technique("B", parents=["A"])
        graph.add_technique("C", parents=["B"])
        assert graph.get_generation("A") == 0
        assert graph.get_generation("B") == 1
        assert graph.get_generation("C") == 2

    def test_len(self):
        graph = GenealogyGraph()
        graph.add_technique("A")
        graph.add_technique("B")
        assert len(graph) == 2

    def test_contains(self):
        graph = GenealogyGraph()
        graph.add_technique("A")
        assert "A" in graph
        assert "B" not in graph
