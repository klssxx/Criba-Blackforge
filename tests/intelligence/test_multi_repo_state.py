"""Regression tests for IIE continuation metadata."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_state_tool():
    root = Path(__file__).resolve().parents[2]
    path = root / ".hermes" / "iie" / "multi_repo_state.py"
    spec = importlib.util.spec_from_file_location("test_multi_repo_state_tool", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_validate_accepts_metadata_only_commit_ahead(tmp_path: Path, monkeypatch, capsys):
    """A checkpoint commit cannot self-reference its eventual own hash."""
    tool = _load_state_tool()
    state_path = tmp_path / "STATE.json"
    state_path.write_text(json.dumps({
        "repos": {
            "CRIBA": {
                "branch": "feat/iie-master",
                "commit": "code-commit",
                "last_good_commit": "code-commit",
            },
            "BLACKFORGE": {
                "branch": "feat/iie-master",
                "commit": "code-commit",
            },
        },
        "locks": [],
    }), encoding="utf-8")

    monkeypatch.setattr(tool, "STATE_PATH", state_path)
    monkeypatch.setattr(tool, "PHYSICAL_REPOS", {"CRIBA": "C:/fake"})
    monkeypatch.setattr(tool, "_live_physical_repo", lambda _: {
        "path": "C:/fake",
        "branch": "feat/iie-master",
        "commit": "metadata-commit",
        "dirty_files": [],
        "is_repo": True,
    })
    monkeypatch.setattr(
        tool,
        "_git",
        lambda _repo, *args: ".hermes/iie/STATE.json\n" if args == (
            "diff", "--name-only", "code-commit..HEAD"
        ) else "",
    )

    assert tool.validate() == 0
    assert "STATE_METADATA_AHEAD" in capsys.readouterr().out
