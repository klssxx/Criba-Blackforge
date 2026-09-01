"""Tests for chain persistence and cold reconstruction."""
from __future__ import annotations

from pathlib import Path

import pytest

from criba.chain import ChainMemory, ChainRunner
from criba.storage import Storage


@pytest.fixture
def tmp_storage(tmp_path: Path) -> Storage:
    return Storage(tmp_path / "test.sqlite3")


class TestChainPersistence:
    def test_chain_session_saved(self, tmp_storage: Storage) -> None:
        runner = ChainRunner(storage=tmp_storage)
        memory = ChainMemory(original_objective="test objective")
        runner.run_stage(1, memory, {"original_query": "test"})
        session = tmp_storage.load_chain_session(memory.chain_id)
        assert session["original_objective"] == "test objective"

    def test_chain_memory_saved(self, tmp_storage: Storage) -> None:
        runner = ChainRunner(storage=tmp_storage)
        memory = ChainMemory(original_objective="test")
        runner.run_stage(1, memory, {"original_query": "test"})
        rows = tmp_storage.load_chain_memory(memory.chain_id)
        assert len(rows) >= 1

    def test_chain_memory_saved_per_stage(self, tmp_storage: Storage) -> None:
        runner = ChainRunner(storage=tmp_storage)
        memory = ChainMemory(original_objective="test")
        for stage in range(1, 4):
            runner.run_stage(stage, memory, {"original_query": "test"})
        rows = tmp_storage.load_chain_memory(memory.chain_id)
        # Should have memory saved for stages 1, 2, 3
        stages_saved = {r["stage"] for r in rows}
        assert 1 in stages_saved
        assert 2 in stages_saved
        assert 3 in stages_saved

    def test_chain_session_updated(self, tmp_storage: Storage) -> None:
        runner = ChainRunner(storage=tmp_storage)
        memory = ChainMemory(original_objective="test")
        runner.run_stage(1, memory, {"original_query": "test"})
        runner.run_stage(2, memory, {"original_query": "test"})
        session = tmp_storage.load_chain_session(memory.chain_id)
        assert session["current_stage"] == 2


class TestColdReconstruction:
    def test_cold_reconstruct(self, tmp_storage: Storage) -> None:
        runner = ChainRunner(storage=tmp_storage)
        memory = ChainMemory(original_objective="test objective")
        runner.run_stage(1, memory, {"original_query": "test"})
        runner.run_stage(2, memory, {"original_query": "test"})
        result = runner.cold_reconstruct(memory.chain_id)
        assert result["session"]["original_objective"] == "test objective"
        assert result["total_records"] >= 1

    def test_cold_reconstruct_no_storage(self) -> None:
        runner = ChainRunner(storage=None)
        with pytest.raises(ValueError, match="Storage no configurado"):
            runner.cold_reconstruct("nonexistent")

    def test_cold_reconstruct_nonexistent(self, tmp_storage: Storage) -> None:
        runner = ChainRunner(storage=tmp_storage)
        with pytest.raises(ValueError, match="Chain inexistente"):
            runner.cold_reconstruct("nonexistent")


class TestPersistFlag:
    def test_persist_disabled(self, tmp_storage: Storage) -> None:
        runner = ChainRunner(storage=tmp_storage, persist=False)
        memory = ChainMemory(original_objective="test")
        runner.run_stage(1, memory, {"original_query": "test"})
        # Should not raise, but nothing persisted
        rows = tmp_storage.load_chain_memory(memory.chain_id)
        assert len(rows) == 0
