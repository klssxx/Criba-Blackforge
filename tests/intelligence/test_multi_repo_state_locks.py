"""Adversarial tests for the fenced multi-repo STATE locks (v2.2).

Covers what the FRONTERAS_CONCURRENCIA prototype proved only in isolation,
now against the real tool: atomic single-winner grants under real thread and
process races, CRIBA/BLACKFORGE alias conflicts, overlapping-scope rejection
without over-blocking disjoint scopes, fence tokens that reject stale
holders after recovery, and recovery after interrupted writes.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = ROOT / ".hermes" / "iie" / "multi_repo_state.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("fenced_state_tool", TOOL_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _seed(path: Path, locks: list[dict] | None = None, **extra) -> Path:
    path.write_text(
        json.dumps({"repos": {}, "locks": locks or [], **extra}), encoding="utf-8"
    )
    return path


@pytest.fixture()
def tool(tmp_path: Path):
    module = _load_tool()
    module.STATE_PATH = tmp_path / "STATE.json"
    _seed(module.STATE_PATH)
    return module


# --- exclusion atómica -------------------------------------------------------

def test_real_thread_race_has_single_winner(tool, tmp_path):
    for round_index in range(30):
        state = tmp_path / f"STATE-{round_index}.json"
        _seed(state)
        tool.STATE_PATH = state
        barrier = threading.Barrier(2, timeout=10)

        def worker(index: int) -> bool:
            barrier.wait()
            return tool.acquire_lock("CRIBA", "src/criba/engine.py", f"h{index}", "r")

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker, i) for i in range(2)]
            grants = [future.result(timeout=20) for future in futures]
        assert sum(grants) == 1, f"round {round_index}: {grants}"
        assert len(json.loads(state.read_text(encoding="utf-8"))["locks"]) == 1


def test_cli_process_race_has_single_winner(tmp_path):
    workdir = tmp_path / "cli"
    workdir.mkdir()
    shutil.copy(TOOL_PATH, workdir / "multi_repo_state.py")
    for round_index in range(3):
        _seed(workdir / "STATE.json")
        procs = [
            subprocess.Popen(
                [sys.executable, str(workdir / "multi_repo_state.py"),
                 "lock", "acquire", "CRIBA", "src/criba/engine.py", f"h{i}", "r"],
                stdout=subprocess.PIPE, text=True,
            )
            for i in range(2)
        ]
        outs = [proc.communicate(timeout=60)[0] for proc in procs]
        codes = [proc.returncode for proc in procs]
        winners = [
            out for out, code in zip(outs, codes)
            if "LOCK_ACQUIRED" in out and code == 0
        ]
        assert len(winners) == 1, f"round {round_index}: {outs} {codes}"


def test_disjoint_scopes_progress_in_parallel(tool):
    barrier = threading.Barrier(2, timeout=10)

    def worker(path: str) -> bool:
        barrier.wait()
        return tool.acquire_lock("CRIBA", path, "same-holder", "r")

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker, p) for p in ("src/a.py", "src/b.py")]
        grants = [future.result(timeout=20) for future in futures]
    assert grants == [True, True]


# --- aliases y solapamiento --------------------------------------------------

def test_alias_criba_blackforge_conflicts(tool):
    assert tool.acquire_lock("CRIBA", "src/criba/blackforge_pipeline.py", "a", "r")
    assert not tool.acquire_lock("BLACKFORGE", "src/criba/blackforge_pipeline.py", "b", "r")
    assert not tool.acquire_lock("CRIBA", r"SRC\CRIBA\BlackForge_PIPELINE.PY", "b", "r")


def test_alias_does_not_overblock_disjoint_paths(tool):
    assert tool.acquire_lock("CRIBA", "src/criba/blackforge_pipeline.py", "a", "r")
    assert tool.acquire_lock("BLACKFORGE", "src/criba/blackforge_catalog.py", "b", "r")
    assert tool.acquire_lock("SUPRA", "src/criba/blackforge_pipeline.py", "c", "r")


def test_parent_child_conflict_both_directions_even_same_holder(tool):
    assert tool.acquire_lock("CRIBA", "src", "a", "r")
    assert not tool.acquire_lock("CRIBA", "src/x.py", "b", "r")
    assert not tool.acquire_lock("CRIBA", "src/x.py", "a", "r")


def test_reentrant_exact_scope_same_holder(tool):
    assert tool.acquire_lock("CRIBA", "src/x.py", "a", "r")
    assert tool.acquire_lock("CRIBA", "src/x.py", "a", "r-again")
    locks = json.loads(tool.STATE_PATH.read_text(encoding="utf-8"))["locks"]
    assert len(locks) == 1 and locks[0]["reason"] == "r"


def test_traversal_is_rejected(tool):
    with pytest.raises(ValueError):
        tool.acquire_lock("CRIBA", "src/../outside.py", "a", "r")
    assert tool.main(["mrs", "lock", "acquire", "CRIBA", "src/../x", "a", "r"]) == 2


# --- versiones y permisos antiguos (fencing) ---------------------------------

def test_fenced_token_rejects_stale_holder_after_recovery(tool):
    assert tool.acquire_lock("CRIBA", "src/x.py", "dead", "r")
    recovered = tool.recover_lock("CRIBA", "src/x.py", "alive", "interrupted")
    assert recovered is not None
    token = recovered["token"]
    dead_token = recovered["token"] - 1
    assert token > dead_token
    assert not tool.release_lock("CRIBA", "src/x.py", "dead")
    assert not tool.release_lock("CRIBA", "src/x.py", "dead", dead_token)
    assert not tool.release_lock("CRIBA", "src/x.py", "alive", dead_token)
    assert tool.release_lock("CRIBA", "src/x.py", "alive", token)


def test_stale_holder_cannot_reacquire_or_publish(tool):
    assert tool.acquire_lock("CRIBA", "src/x.py", "dead", "r")
    assert tool.recover_lock("CRIBA", "src/x.py", "alive", "interrupted")
    assert not tool.acquire_lock("CRIBA", "src/x.py", "dead", "r")


def test_recover_on_free_scope_acts_as_acquire(tool):
    entry = tool.recover_lock("CRIBA", "src/x.py", "a", "r")
    assert entry is not None and entry["token"] == 1
    assert not tool.acquire_lock("CRIBA", "src/x.py", "b", "r")


def test_recover_refuses_overlap_only_scope(tool):
    assert tool.acquire_lock("CRIBA", "src", "a", "r")
    assert tool.recover_lock("CRIBA", "src/x.py", "b", "r") is None
    assert tool.acquire_lock("CRIBA", "src/x.py", "b", "r") is False


def test_cli_recover_and_fenced_release(tool, capsys):
    assert tool.acquire_lock("CRIBA", "src/x.py", "dead", "r")
    assert tool.main(["mrs", "lock", "recover", "CRIBA", "src/x.py", "alive", "r2"]) == 0
    assert "LOCK_RECOVERED" in capsys.readouterr().out
    assert tool.main(["mrs", "lock", "release", "CRIBA", "src/x.py", "dead"]) == 0
    assert "LOCK_NOT_FOUND" in capsys.readouterr().out


# --- compatibilidad con estados legacy ---------------------------------------

def test_legacy_state_without_tokens_still_works(tool, monkeypatch):
    _seed(
        tool.STATE_PATH,
        locks=[{
            "repo": "CRIBA", "path": "src/a.py", "holder": "legacy",
            "acquired_at": "t", "reason": "r",
        }],
        repos={
            "CRIBA": {"branch": "b", "commit": "c1", "last_good_commit": "c1"},
            "SUPRA": {"branch": "main", "commit": "c1", "last_good_commit": "c1"},
            "BLACKFORGE": {"branch": "b", "commit": "c1"},
        },
    )
    monkeypatch.setattr(tool, "PHYSICAL_REPOS", {"CRIBA": "x", "SUPRA": "y"})
    monkeypatch.setattr(tool, "_live_physical_repo", lambda _: {
        "path": "x", "branch": "b", "commit": "c1", "dirty_files": [], "is_repo": True,
    })
    assert not tool.acquire_lock("CRIBA", "src/a.py", "other", "r")
    assert tool.acquire_lock("CRIBA", "src/b.py", "new", "r")
    assert tool.release_lock("CRIBA", "src/a.py", "legacy")
    assert tool.validate() == 0


def test_validate_reports_residual_overlaps(tool):
    _seed(tool.STATE_PATH, locks=[
        {"repo": "CRIBA", "path": "src", "holder": "a",
         "acquired_at": "t", "reason": "r"},
        {"repo": "CRIBA", "path": "src/x.py", "holder": "b",
         "acquired_at": "t", "reason": "r"},
    ])
    assert tool.validate() == 2


# --- recuperación tras interrupciones ----------------------------------------

def test_snapshot_restores_state_from_bak_after_corruption(tmp_path, monkeypatch):
    tool = _load_tool()
    state = tmp_path / "STATE.json"
    _seed(state, locks=[{"repo": "CRIBA", "path": "src/a.py", "holder": "h",
                         "acquired_at": "t", "reason": "r"}])
    tool.STATE_PATH = state
    assert tool.acquire_lock("CRIBA", "src/b.py", "h", "r")  # creates .bak of pre-acquire state
    state.write_text('{"repos": {"CRIBA": {"com', encoding="utf-8")  # torn write
    monkeypatch.setattr(tool, "PHYSICAL_REPOS", {"CRIBA": "C:/fake"})
    monkeypatch.setattr(tool, "_live_physical_repo", lambda _: {
        "path": "C:/fake", "branch": "b", "commit": "metadata-commit",
        "dirty_files": [], "is_repo": True,
    })
    live = tool.snapshot()
    assert live["last_recovery"]["action"] == "restore_from_bak"
    restored = json.loads(state.read_text(encoding="utf-8"))
    assert {lock["path"] for lock in restored["locks"]} == {"src/a.py"}
    assert restored["repos"]["CRIBA"]["commit"] == "metadata-commit"


def test_corrupt_state_without_bak_fails_loudly(tool):
    tool.STATE_PATH.write_text("{corrupt", encoding="utf-8")
    with pytest.raises(RuntimeError):
        tool.acquire_lock("CRIBA", "src/x.py", "a", "r")


def test_atomic_write_leaves_no_tmp_files(tool):
    for path in ("src/a.py", "src/b.py"):
        assert tool.acquire_lock("CRIBA", path, "h", "r")
    assert tool.release_lock("CRIBA", "src/a.py", "h")
    assert list(tool.STATE_PATH.parent.glob("*.tmp")) == []


def test_tokens_are_monotonic_across_scopes(tool):
    assert tool.acquire_lock("CRIBA", "src/a.py", "a", "r")
    assert tool.release_lock("CRIBA", "src/a.py", "a")
    assert tool.acquire_lock("CRIBA", "src/b.py", "b", "r")
    locks = json.loads(tool.STATE_PATH.read_text(encoding="utf-8"))["locks"]
    assert locks[0]["token"] == 2
