"""Tests for task_layer.py — HIPERMEGAPROMPT §3."""
from __future__ import annotations

from criba.task_layer import (
    BLACKFORGE_EXTENSION,
    BLACKFORGE_SEQUENCE,
    CRIBA_SEQUENCE,
    BlackforgeTaskType,
    CribaTaskType,
    TaskDefinition,
    define_task,
    validate_sequence,
)

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestTaskTypes:
    def test_criba_types_count(self) -> None:
        assert len(CribaTaskType) == 7

    def test_blackforge_types_count(self) -> None:
        assert len(BlackforgeTaskType) == 8

    def test_criba_types_values(self) -> None:
        expected = {"generation", "evaluation", "improvement", "disruption",
                    "convergence", "research", "design"}
        assert {t.value for t in CribaTaskType} == expected


# ---------------------------------------------------------------------------
# Sequences
# ---------------------------------------------------------------------------

class TestSequences:
    def test_criba_sequence_length(self) -> None:
        assert len(CRIBA_SEQUENCE) == 10

    def test_blackforge_extension_length(self) -> None:
        assert len(BLACKFORGE_EXTENSION) == 4

    def test_blackforge_full_length(self) -> None:
        assert len(BLACKFORGE_SEQUENCE) == 14

    def test_blackforge_starts_with_criba(self) -> None:
        assert BLACKFORGE_SEQUENCE[:10] == CRIBA_SEQUENCE

    def test_criba_first_step(self) -> None:
        assert CRIBA_SEQUENCE[0] == "INTERPRET"

    def test_criba_last_step(self) -> None:
        assert CRIBA_SEQUENCE[-1] == "CONCLUDE"

    def test_blackforge_last_steps(self) -> None:
        assert BLACKFORGE_SEQUENCE[-4:] == ["ADVERSARIALIZE", "CONTAIN", "DETECT", "RECOVER"]


# ---------------------------------------------------------------------------
# validate_sequence
# ---------------------------------------------------------------------------

class TestValidateSequence:
    def test_empty_valid(self) -> None:
        result = validate_sequence([], "criba")
        assert result.is_valid
        assert result.expected_next == ["INTERPRET"]

    def test_valid_full_criba(self) -> None:
        result = validate_sequence(CRIBA_SEQUENCE, "criba")
        assert result.is_valid
        assert result.missing_steps == []

    def test_valid_partial(self) -> None:
        result = validate_sequence(["INTERPRET", "DELIMIT"], "criba")
        assert result.is_valid
        assert result.current_step == "DELIMIT"
        assert result.expected_next == ["CARTOGRAPH"]

    def test_invalid_order(self) -> None:
        result = validate_sequence(["GENERATE", "INTERPRET"], "criba")
        assert not result.is_valid
        assert len(result.violations) > 0

    def test_unknown_step(self) -> None:
        result = validate_sequence(["INTERPRET", "FAKESTEP"], "criba")
        assert not result.is_valid
        assert any("FAKESTEP" in v for v in result.violations)

    def test_blackforge_full(self) -> None:
        result = validate_sequence(BLACKFORGE_SEQUENCE, "blackforge")
        assert result.is_valid
        assert result.missing_steps == []

    def test_blackforge_missing_extension(self) -> None:
        result = validate_sequence(CRIBA_SEQUENCE, "blackforge")
        assert result.is_valid  # all steps valid, just not complete
        assert "ADVERSARIALIZE" in result.missing_steps

    def test_completed_steps_preserved(self) -> None:
        result = validate_sequence(["INTERPRET", "DELIMIT", "CARTOGRAPH"], "criba")
        assert result.completed_steps == ["INTERPRET", "DELIMIT", "CARTOGRAPH"]


# ---------------------------------------------------------------------------
# TaskDefinition
# ---------------------------------------------------------------------------

class TestTaskDefinition:
    def test_defaults(self) -> None:
        task = TaskDefinition()
        assert task.task_id  # auto-generated
        assert task.operating_mode == "criba"
        assert task.final_status == "pending"

    def test_custom(self) -> None:
        task = TaskDefinition(
            operating_mode="blackforge",
            task_type="pentesting",
            primary_objective="Test API security",
        )
        assert task.operating_mode == "blackforge"
        assert task.task_type == "pentesting"

    def test_serialization_roundtrip(self) -> None:
        task = TaskDefinition(task_type="generation", primary_objective="Generate ideas")
        data = task.model_dump()
        restored = TaskDefinition(**data)
        assert restored.task_type == "generation"


# ---------------------------------------------------------------------------
# define_task
# ---------------------------------------------------------------------------

class TestDefineTask:
    def test_criba_task(self) -> None:
        task = define_task("test query", mode="criba")
        assert task.operating_mode == "criba"
        assert task.execution_sequence == CRIBA_SEQUENCE
        assert task.convergence_conditions
        assert task.rejection_conditions

    def test_blackforge_task(self) -> None:
        task = define_task("pentest API", mode="blackforge")
        assert task.operating_mode == "blackforge"
        assert task.execution_sequence == BLACKFORGE_SEQUENCE

    def test_query_element_used(self) -> None:
        q = "A" * 300
        task = define_task(q)
        assert len(task.query_element_used) == 200
