"""Multi-repo IIE continuation state tooling (P05).

Tracks physical repositories CRIBA and SUPRA, plus BLACKFORGE as a logical
project inside CRIBA. Locks are scoped by repository and path.

Usage:
  python multi_repo_state.py snapshot
  python multi_repo_state.py validate
  python multi_repo_state.py lock list
  python multi_repo_state.py lock acquire <repo> <path> <holder> <reason>
  python multi_repo_state.py lock release <repo> <path> <holder>
"""
from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
STATE_PATH = ROOT / "STATE.json"
PHYSICAL_REPOS: dict[str, str] = {
    "CRIBA": "C:/Users/KLSX/Music/INNOVATIONS/ACTIVE/CRIBA",
    "SUPRA": "C:/Users/KLSX/Music/INNOVATIONS/ACTIVE/SUPRA",
}
BLACKFORGE_PATHS: tuple[str, ...] = ("src/criba/blackforge_",)
LOCK_FIELDS = {"repo", "path", "holder", "acquired_at", "reason"}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _read_state() -> dict[str, Any]:
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def _write_state(state: dict[str, Any]) -> None:
    state["last_updated"] = _now()
    STATE_PATH.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _git(repo: str, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _live_physical_repo(repo_path: str) -> dict[str, Any]:
    head = _git(repo_path, "rev-parse", "HEAD")
    return {
        "path": repo_path,
        "branch": _git(repo_path, "rev-parse", "--abbrev-ref", "HEAD"),
        "commit": head,
        "tags_at_head": [
            tag for tag in _git(repo_path, "tag", "--points-at", "HEAD").splitlines()
            if tag
        ],
        "dirty_files": _git(repo_path, "status", "--porcelain").splitlines(),
        "is_repo": bool(head),
    }


def _changed_paths_since(repo_path: str, recorded_commit: str) -> list[str]:
    """Return paths changed after a recorded snapshot, if Git can resolve it."""
    if not recorded_commit:
        return []
    return [
        path for path in _git(repo_path, "diff", "--name-only", f"{recorded_commit}..HEAD").splitlines()
        if path
    ]


def _is_metadata_only_advance(paths: list[str]) -> bool:
    """A checkpoint commit is allowed to advance HEAD without self-reference."""
    return bool(paths) and all(path.startswith(".hermes/iie/") for path in paths)


def _blackforge_state(criba: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
    """Represent BLACKFORGE without pretending it has its own Git repository."""
    return {
        "repo_path": criba["path"],
        "shared_repo": "CRIBA",
        "sector_paths": list(BLACKFORGE_PATHS),
        "branch": criba["branch"],
        "commit": criba["commit"],
        "dirty_files": [
            entry for entry in criba["dirty_files"]
            if any(path in entry for path in BLACKFORGE_PATHS)
        ],
        "is_repo": False,
        "baseline_commit": previous.get("baseline_commit") or criba["baseline_commit"],
        "last_good_commit": previous.get("last_good_commit") or criba["last_good_commit"],
        "last_good_tests": previous.get("last_good_tests", []),
    }


def snapshot() -> dict[str, Any]:
    """Update physical-repository snapshots and the logical BLACKFORGE record."""
    state = _read_state()
    repos = state.setdefault("repos", {})
    for key, path in PHYSICAL_REPOS.items():
        previous = repos.get(key, {})
        live = _live_physical_repo(path)
        live["baseline_commit"] = previous.get("baseline_commit") or live["commit"]
        live["last_good_commit"] = previous.get("last_good_commit") or live["commit"]
        live["last_good_tests"] = previous.get("last_good_tests", [])
        repos[key] = live
    repos["BLACKFORGE"] = _blackforge_state(repos["CRIBA"], repos.get("BLACKFORGE", {}))
    state["state_schema_note"] = "per-repo branch/commit/dirty; locks per repo+path (v2.1)"
    state.setdefault("locks", [])
    _write_state(state)
    return state


def validate() -> int:
    """Run resume detection without modifying state.

    Return nonzero for a stale/missing structural record. A dirty worktree is
    reported as DIRTY but is not silently treated as a valid verified point.
    """
    state = _read_state()
    repos = state.get("repos", {})
    problems: list[str] = []
    print("RESUME DETECTION (per-repo)")
    for key, path in PHYSICAL_REPOS.items():
        live = _live_physical_repo(path)
        recorded = repos.get(key)
        print(f"\n[{key}] {path}")
        print(f"  branch={live['branch']} head={live['commit'][:12]} dirty={len(live['dirty_files'])}")
        if not recorded:
            problems.append(f"{key}: no STATE record (run snapshot)")
            continue
        print(
            f"  state: branch={recorded.get('branch')} "
            f"commit={str(recorded.get('commit'))[:12]} "
            f"last_good={str(recorded.get('last_good_commit'))[:12]}"
        )
        if recorded.get("commit") != live["commit"]:
            changed_paths = _changed_paths_since(path, str(recorded.get("commit") or ""))
            if _is_metadata_only_advance(changed_paths):
                print("  classification=STATE_METADATA_AHEAD")
            else:
                problems.append(f"{key}: STATE_STALE (recorded commit != HEAD)")
        elif live["dirty_files"]:
            print("  classification=DIRTY")
        else:
            print("  classification=SYNCED")

    blackforge = repos.get("BLACKFORGE")
    criba = repos.get("CRIBA")
    if not blackforge:
        problems.append("BLACKFORGE: no logical project record")
    elif not criba or any(blackforge.get(key) != criba.get(key) for key in ("branch", "commit")):
        problems.append("BLACKFORGE: STATE_STALE against shared CRIBA repo")

    locks = state.get("locks", [])
    print(f"\nlocks activos: {len(locks)}")
    for lock in locks:
        missing = sorted(LOCK_FIELDS - set(lock))
        if missing:
            problems.append(f"lock malformed: missing {','.join(missing)}")
        if lock.get("repo") not in {*PHYSICAL_REPOS, "BLACKFORGE"}:
            problems.append(f"lock invalid repo: {lock.get('repo')}")
        print(json.dumps(lock, ensure_ascii=False, sort_keys=True))

    if problems:
        print("\nDISCREPANCIAS:\n- " + "\n- ".join(problems))
        return 2
    print("\nOK: estructura consistente; usar clasificación DIRTY antes de reanudar")
    return 0


def acquire_lock(repo: str, path: str, holder: str, reason: str) -> bool:
    """Acquire a reentrant single-writer lock; false means another holder owns it."""
    state = _read_state()
    locks = state.setdefault("locks", [])
    for lock in locks:
        if lock.get("repo") == repo and lock.get("path") == path:
            return lock.get("holder") == holder
    locks.append(
        {
            "repo": repo,
            "path": path,
            "holder": holder,
            "acquired_at": _now(),
            "reason": reason,
        }
    )
    _write_state(state)
    return True


def release_lock(repo: str, path: str, holder: str) -> bool:
    """Release only the caller's lock and report whether one was removed."""
    state = _read_state()
    locks = state.get("locks", [])
    kept = [
        lock for lock in locks
        if not (lock.get("repo") == repo and lock.get("path") == path and lock.get("holder") == holder)
    ]
    released = len(kept) != len(locks)
    state["locks"] = kept
    _write_state(state)
    return released


def _usage() -> str:
    return (
        "usage: multi_repo_state.py snapshot|validate|lock "
        "list|acquire <repo> <path> <holder> <reason>|release <repo> <path> <holder>"
    )


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else ""
    if command == "snapshot":
        state = snapshot()
        print("SNAPSHOT_OK", {key: value["commit"][:12] for key, value in state["repos"].items()})
        return 0
    if command == "validate":
        return validate()
    if command == "lock":
        action = argv[2] if len(argv) > 2 else ""
        if action == "list":
            for lock in _read_state().get("locks", []):
                print(json.dumps(lock, ensure_ascii=False, sort_keys=True))
            return 0
        if action == "acquire" and len(argv) == 7:
            acquired = acquire_lock(argv[3], argv[4], argv[5], argv[6])
            print("LOCK_ACQUIRED" if acquired else "LOCK_CONFLICT")
            return 0 if acquired else 3
        if action == "release" and len(argv) == 6:
            print("LOCK_RELEASED" if release_lock(argv[3], argv[4], argv[5]) else "LOCK_NOT_FOUND")
            return 0
    print(_usage())
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
