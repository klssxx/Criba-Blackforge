"""Test SQLite persistence and cross-session deduplication in LotteryEngine."""
import tempfile
from pathlib import Path

from criba.catalog import methods
from criba.lottery import LotteryEngine
from criba.storage import Storage


def test_lottery_sqlite_cross_session_deduplication():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_lottery.sqlite3"
        store = Storage(db_path)

        all_methods = methods()[:30]  # Small subset for fast test

        # 1. First Engine session
        engine1 = LotteryEngine.from_methods(all_methods, seed=42, storage=store)
        stats1 = engine1.run_round(mode="pure", batch_size=6)
        combos1_count = len(engine1.used_combos)
        assert combos1_count > 0

        # Check that combinations were saved to SQLite
        loaded_combos = store.load_used_lottery_combinations(engine1.catalog_fingerprint)
        assert len(loaded_combos) == combos1_count

        # 2. Second Engine session (new instance representing a process restart)
        engine2 = LotteryEngine.from_methods(all_methods, seed=999, storage=store)
        # Verify it reloaded all combinations from previous session
        assert len(engine2.used_combos) == combos1_count
        assert engine2.used_combos == engine1.used_combos

        # Run a round on engine2: all previous combinations must be skipped
        stats2 = engine2.run_round(mode="pure", batch_size=6)
        # Any newly generated ideas must NOT intersect with engine1 ideas
        for idea in engine2.last_round_ideas:
            m1_id, m2_id = str(idea["method1"]), str(idea["method2"])
            # The combo was not in engine1
            pair = (min(m1_id, m2_id), max(m1_id, m2_id))
            assert pair not in engine1.last_round_ideas
