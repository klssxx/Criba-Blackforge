"""Multi-repo IIE continuation state tooling (P05).

Tracks physical repositories CRIBA and SUPRA, plus BLACKFORGE as a logical
project inside CRIBA. Locks are scoped by repository and path.

Locks are single-writer and fenced: acquisition is atomic across threads and
processes (a file mutex serializes every mutation of STATE.json, which is
replaced atomically and backed up to STATE.json.bak), each grant carries a
monotonic token, overlapping scopes conflict (parent/child path prefix, and
BLACKFORGE locks compete with CRIBA locks because BLACKFORGE lives inside the
CRIBA worktree), and `lock recover` takes over a scope from an interrupted
holder while fencing the previous token. Disjoint scopes always progress.

Limits, stated plainly: only writers that go through this module are
serialized; a hand edit of STATE.json can still corrupt it (validate detects
overlapping/unknown locks, snapshot restores from .bak after a torn write).
There is no lease expiry: a crashed holder blocks its scope until `recover`.
This tool does not authenticate evidence/VERIFIED and does not protect files
themselves, only the coordination record.

Usage:
  python multi_repo_state.py snapshot
  python multi_repo_state.py validate
  python multi_repo_state.py lock list
  python multi_repo_state.py lock acquire <repo> <path> <holder> <reason>
  python multi_repo_state.py lock release <repo> <path> <holder> [token]
  python multi_repo_state.py lock recover <repo> <path> <holder> <reason>
"""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

try:  # Windows byte-range lock; POSIX falls back to flock.
    import msvcrt
except ImportError:  # pragma: no cover - CI/linux path
    msvcrt = None  # type: ignore[assignment]
    import fcntl

ROOT = Path(__file__).resolve().parent
STATE_PATH = ROOT / "STATE.json"
PHYSICAL_REPOS: dict[str, str] = {
    "CRIBA": "C:/Users/KLSX/Music/INNOVATIONS/ACTIVE/CRIBA",
    "SUPRA": "C:/Users/KLSX/Music/INNOVATIONS/ACTIVE/SUPRA",
}
BLACKFORGE_PATHS: tuple[str, ...] = ("src/criba/blackforge_",)
LOCK_FIELDS = {"repo", "path", "holder", "acquired_at", "reason"}
# BLACKFORGE is a logical project sharing the CRIBA repository: its locks must
# compete with CRIBA locks on the same paths.
_ALIAS_PHYSICAL = {"BLACKFORGE": "CRIBA"}
_MUTEX_TIMEOUT_SECONDS = 30.0


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _sidecar(suffix: str) -> Path:
    return STATE_PATH.parent / (STATE_PATH.name + suffix)


def _mutex_path() -> Path:
    return _sidecar(".lock")


@contextmanager
def _state_mutex() -> Iterator[None]:
    """Serialize writers across threads and processes.

    Every mutation of STATE.json runs under this exclusive file lock; readers
    need no lock because writes replace the file atomically. Locks are per
    handle, so separate handles in one process contend correctly.
    """
    path = _mutex_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o666)
    deadline = time.monotonic() + _MUTEX_TIMEOUT_SECONDS
    try:
        while True:
            try:
                if msvcrt is not None:
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"STATE mutex busy for {_MUTEX_TIMEOUT_SECONDS}s: {path}"
                    ) from None
                time.sleep(0.02)
        yield
    finally:
        try:
            if msvcrt is not None:
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(fd)


def _read_state() -> dict[str, Any]:
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def _read_state_or_repair() -> dict[str, Any]:
    """Read STATE.json; after a torn write restore the last complete .bak.

    Only mutating operations (which run under the mutex) use this path;
    validate keeps the strict read-only behavior of plain _read_state.
    """
    try:
        return _read_state()
    except json.JSONDecodeError as exc:
        backup = _sidecar(".bak")
        if not backup.exists():
            raise RuntimeError(
                f"{STATE_PATH.name} is corrupt and no {backup.name} exists"
            ) from exc
        state = json.loads(backup.read_text(encoding="utf-8"))
        state["last_recovery"] = {"at": _now(), "action": "restore_from_bak"}
        STATE_PATH.unlink(missing_ok=True)  # keep the good .bak from being overwritten
        _write_state(state)
        return state


def _write_state(state: dict[str, Any]) -> None:
    state["last_updated"] = _now()
    payload = json.dumps(state, indent=2, ensure_ascii=False) + "\n"
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if STATE_PATH.exists():
        # Last complete copy for _read_state_or_repair; taken before the
        # replace so a crash mid-write never destroys both copies.
        shutil.copyfile(STATE_PATH, _sidecar(".bak"))
    tmp = _sidecar(".tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, STATE_PATH)


def _lock_scope(repo: str, path: str) -> tuple[str, str]:
    """Conflict key for a lock: (physical repo, normalized relative path).

    BLACKFORGE maps onto CRIBA (shared worktree), path separators normalize to
    '/', empty/`.` components drop, and comparison is case-insensitive to match
    Windows. Parent traversal is rejected outright.
    """
    if not isinstance(repo, str) or not repo:
        raise ValueError("repo must be a nonempty string")
    if not isinstance(path, str) or not path:
        raise ValueError("path must be a nonempty string")
    parts = path.replace("\\", "/").split("/")
    if any(part == ".." for part in parts):
        raise ValueError("parent traversal is forbidden in lock paths")
    normalized = "/".join(part for part in parts if part not in ("", ".")).casefold()
    if not normalized:
        raise ValueError("path must name a file or directory")
    return _ALIAS_PHYSICAL.get(repo, repo), normalized


def _overlaps(left: tuple[str, str], right: tuple[str, str]) -> bool:
    """True when the scopes touch: same physical repo and prefix-related paths."""
    if left[0] != right[0]:
        return False
    a, b = left[1], right[1]
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def _entry_scope(lock: dict[str, Any]) -> tuple[str, str] | None:
    try:
        return _lock_scope(str(lock.get("repo")), str(lock.get("path")))
    except ValueError:
        return None  # malformed entries are reported by validate, never crash it


def _next_token(state: dict[str, Any]) -> int:
    """Monotonic fence token; survives across scopes via state['lock_seq']."""
    seq = int(state.get("lock_seq", 0))
    for lock in state.get("locks", []):
        seq = max(seq, int(lock.get("token") or 0))
    state["lock_seq"] = seq + 1
    return seq + 1


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
    live = {key: _live_physical_repo(path) for key, path in PHYSICAL_REPOS.items()}
    with _state_mutex():
        state = _read_state_or_repair()
        repos = state.setdefault("repos", {})
        for key, live_repo in live.items():
            previous = repos.get(key, {})
            live_repo["baseline_commit"] = previous.get("baseline_commit") or live_repo["commit"]
            live_repo["last_good_commit"] = previous.get("last_good_commit") or live_repo["commit"]
            live_repo["last_good_tests"] = previous.get("last_good_tests", [])
            repos[key] = live_repo
        repos["BLACKFORGE"] = _blackforge_state(repos["CRIBA"], repos.get("BLACKFORGE", {}))
        state["state_schema_note"] = (
            "per-repo branch/commit/dirty; fenced atomic locks per repo+path (v2.2)"
        )
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
    lock_scopes: list[tuple[tuple[str, str], dict[str, Any]]] = []
    for lock in locks:
        missing = sorted(LOCK_FIELDS - set(lock))
        if missing:
            problems.append(f"lock malformed: missing {','.join(missing)}")
        if lock.get("repo") not in {*PHYSICAL_REPOS, "BLACKFORGE"}:
            problems.append(f"lock invalid repo: {lock.get('repo')}")
        scope = _entry_scope(lock)
        if scope is not None:
            lock_scopes.append((scope, lock))
        print(json.dumps(lock, ensure_ascii=False, sort_keys=True))
    for i, (left, left_lock) in enumerate(lock_scopes):
        for right, right_lock in lock_scopes[i + 1:]:
            if _overlaps(left, right):
                problems.append(
                    "lock overlap: "
                    f"{left_lock.get('repo')}:{left_lock.get('path')} vs "
                    f"{right_lock.get('repo')}:{right_lock.get('path')}"
                )

    if problems:
        print("\nDISCREPANCIAS:\n- " + "\n- ".join(problems))
        return 2
    print("\nOK: estructura consistente; usar clasificación DIRTY antes de reanudar")
    return 0


def acquire_lock(repo: str, path: str, holder: str, reason: str) -> bool:
    """Acquire a reentrant single-writer lock; false means a conflicting lock.

    Atomic across threads and processes (file mutex). Reentrant for the same
    holder on the exact same scope; any overlapping scope (parent/child path,
    or the CRIBA/BLACKFORGE alias on the shared worktree) conflicts even for
    the same holder. The grant carries a monotonic fence token.
    """
    scope = _lock_scope(repo, path)
    if not isinstance(holder, str) or not holder:
        raise ValueError("holder must be a nonempty string")
    with _state_mutex():
        state = _read_state_or_repair()
        locks = state.setdefault("locks", [])
        for lock in locks:
            if _entry_scope(lock) == scope:
                return lock.get("holder") == holder
        for lock in locks:
            other = _entry_scope(lock)
            if other is not None and _overlaps(scope, other):
                return False
        locks.append(
            {
                "repo": repo,
                "path": path,
                "holder": holder,
                "acquired_at": _now(),
                "reason": reason,
                "token": _next_token(state),
            }
        )
        _write_state(state)
        return True


def release_lock(repo: str, path: str, holder: str, token: int | None = None) -> bool:
    """Release only the caller's lock and report whether one was removed.

    A holder whose scope was taken over by `recover` can no longer release:
    the entry now belongs to the new holder, and passing the old token is
    rejected even if the holder string somehow still matches.
    """
    scope = _lock_scope(repo, path)
    with _state_mutex():
        state = _read_state_or_repair()
        locks = state.get("locks", [])
        kept: list[dict[str, Any]] = []
        released = False
        for lock in locks:
            if (
                _entry_scope(lock) == scope
                and lock.get("holder") == holder
                and (token is None or lock.get("token") == token)
            ):
                released = True
                continue
            kept.append(lock)
        if released:
            state["locks"] = kept
            _write_state(state)
        return released


def recover_lock(repo: str, path: str, new_holder: str, reason: str) -> dict[str, Any] | None:
    """Take over a scope from an interrupted holder, fencing the old token.

    On a held exact scope the entry is replaced (previous holder recorded),
    and the new token supersedes the old one: the previous holder can neither
    release nor re-acquire with its stale permission. On a free scope it acts
    as a fresh acquire. If only non-exact overlapping locks exist it returns
    None instead of creating an overlapping pair.
    """
    scope = _lock_scope(repo, path)
    if not isinstance(new_holder, str) or not new_holder:
        raise ValueError("holder must be a nonempty string")
    with _state_mutex():
        state = _read_state_or_repair()
        locks = state.setdefault("locks", [])
        for lock in locks:
            if _entry_scope(lock) == scope:
                lock.update(
                    {
                        "holder": new_holder,
                        "acquired_at": _now(),
                        "reason": reason,
                        "token": _next_token(state),
                        "recovered_from": lock.get("holder"),
                        "recovered_at": _now(),
                    }
                )
                _write_state(state)
                return lock
        for lock in locks:
            other = _entry_scope(lock)
            if other is not None and _overlaps(scope, other):
                return None
        entry = {
            "repo": repo,
            "path": path,
            "holder": new_holder,
            "acquired_at": _now(),
            "reason": reason,
            "token": _next_token(state),
        }
        locks.append(entry)
        _write_state(state)
        return entry


def _usage() -> str:
    return (
        "usage: multi_repo_state.py snapshot|validate|lock "
        "list|acquire <repo> <path> <holder> <reason>|"
        "release <repo> <path> <holder> [token]|"
        "recover <repo> <path> <holder> <reason>"
    )


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else ""
    try:
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
            if action == "release" and len(argv) in (6, 7):
                token = int(argv[6]) if len(argv) == 7 else None
                released = release_lock(argv[3], argv[4], argv[5], token)
                print("LOCK_RELEASED" if released else "LOCK_NOT_FOUND")
                return 0
            if action == "recover" and len(argv) == 7:
                entry = recover_lock(argv[3], argv[4], argv[5], argv[6])
                if entry is None:
                    print("LOCK_OVERLAP")
                    return 4
                print("LOCK_RECOVERED", json.dumps(entry, ensure_ascii=False, sort_keys=True))
                return 0
    except ValueError as exc:
        print("LOCK_INVALID", exc)
        return 2
    except TimeoutError as exc:
        print("LOCK_BUSY", exc)
        return 5
    print(_usage())
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
