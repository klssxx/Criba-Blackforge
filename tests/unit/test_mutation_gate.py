from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from mutmut.configuration import Config

from scripts import run_mutation_gate


def test_mutmut_copies_package_but_only_mutates_personas(monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.chdir(repo_root)
    Config.reset()
    try:
        config = Config.get()
        assert [path.as_posix() for path in config.source_paths] == ["src"]
        assert Path("data") in config.also_copy
        assert config.should_mutate(Path("src/criba/personas.py"))
        assert not config.should_mutate(Path("src/criba/engine.py"))
    finally:
        Config.reset()


def test_run_shard_uses_mutmut_console_entrypoint(monkeypatch) -> None:
    """Avoid re-executing mutmut.__main__ in forked test workers (GH-466)."""
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return SimpleNamespace(
            returncode=0,
            stdout="killed 1 survived 0",
            stderr="",
        )

    monkeypatch.setattr(run_mutation_gate.subprocess, "run", fake_run)
    monkeypatch.setattr(
        run_mutation_gate,
        "parse_mutmut_summary",
        lambda output: {
            "killed": 1,
            "no_tests": 0,
            "timeout": 0,
            "suspicious": 0,
            "survived": 0,
            "skipped": 0,
        },
    )

    return_code, report = run_mutation_gate.run_shard(
        "criba.personas.x_run_persona__mutmut_*", minimum_score=80.0
    )

    assert captured["command"] == [
        "mutmut",
        "run",
        "criba.personas.x_run_persona__mutmut_*",
        "--max-children",
        "2",
    ]
    assert return_code == 0
    assert report["passed"] is True
    assert report["mutation_score"] == 100.0
