"""Focused contracts for the three CRIBA lottery modes."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from criba.lottery import (
    LotteryEngine,
    default_methods_file,
    default_output_dir,
    run_lottery,
)


def _methods() -> list[dict[str, object]]:
    return [
        {
            "id": "optimized-a",
            "name": "Optimized A",
            "title": "Optimized A",
            "description": "highest ranked method",
            "family": "alpha",
            "quality_score_v2": 100,
        },
        {
            "id": "optimized-b",
            "name": "Optimized B",
            "title": "Optimized B",
            "description": "second highest ranked method",
            "family": "beta",
            "quality_score_v2": 90,
        },
        {
            "id": "associated-a",
            "name": "Associated A",
            "title": "Tema especial A",
            "description": "connected to the requested topic",
            "family": "gamma",
            "quality_score_v2": 1,
        },
        {
            "id": "associated-b",
            "name": "Associated B",
            "title": "Associated B",
            "description": "contains tema especial",
            "family": "delta",
            "quality_score_v2": 2,
        },
        *[
            {
                "id": f"random-{index}",
                "name": f"Random {index}",
                "title": f"Random {index}",
                "description": "unrelated",
                "family": f"random-family-{index % 3}",
                "quality_score_v2": index,
            }
            for index in range(8)
        ],
    ]


def test_optimized_and_associative_modes_apply_distinct_selection_rules() -> None:
    optimized = LotteryEngine.from_methods(_methods(), seed=7)
    associative = LotteryEngine.from_methods(_methods(), seed=7)

    optimized_stats = optimized.run_round("optimized", batch_size=2)
    associative_stats = associative.run_round(
        "associative", batch_size=2, query="tema solicitud"
    )

    assert optimized_stats["mode"] == "optimized"
    assert optimized_stats["method_ids"] == ["optimized-a", "optimized-b"]
    assert associative_stats["mode"] == "associative"
    assert set(associative_stats["method_ids"]) == {"associated-a", "associated-b"}


def test_associative_fallback_is_not_pure_random_sampling() -> None:
    associative = LotteryEngine.from_methods(_methods(), seed=101)
    pure = LotteryEngine.from_methods(_methods(), seed=101)

    associative_stats = associative.run_round(
        "associative", batch_size=4, query="sin coincidencias xyz"
    )
    pure_stats = pure.run_round("pure", batch_size=4)

    assert associative_stats["method_ids"] != pure_stats["method_ids"]
    assert len(associative_stats["families"]) == 4


@pytest.mark.parametrize("mode", ["optimized", "associative", "pure", "alternating"])
def test_seed_reproduces_complete_round_history(mode: str) -> None:
    first = LotteryEngine.from_methods(_methods(), seed=23)
    second = LotteryEngine.from_methods(_methods(), seed=23)

    for _ in range(2):
        first.run_round(mode, batch_size=3, query="tema")
        second.run_round(mode, batch_size=3, query="tema")

    assert first.round_history == second.round_history
    assert first.all_ideas == second.all_ideas


def test_associative_seed_is_reproducible_across_hash_seeds(tmp_path: Path) -> None:
    methods_file = tmp_path / "methods.json"
    methods_file.write_text(json.dumps(_methods()), encoding="utf-8")
    program = (
        "import json,sys; from criba.lottery import LotteryEngine; "
        "engine=LotteryEngine(sys.argv[1], seed=31); "
        "stats=engine.run_round('associative', batch_size=5); "
        "print(json.dumps({'stats': stats, 'ideas': engine.last_round_ideas}, "
        "ensure_ascii=False, sort_keys=True))"
    )

    outputs = []
    for hash_seed in ("1", "987654"):
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = hash_seed
        env["PYTHONIOENCODING"] = "utf-8"
        completed = subprocess.run(
            [sys.executable, "-c", program, str(methods_file)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )
        outputs.append(completed.stdout)

    assert outputs[0] == outputs[1]


def test_consecutive_rounds_never_repeat_method_ids() -> None:
    engine = LotteryEngine.from_methods(_methods(), seed=11)
    rounds = [engine.run_round("pure", batch_size=3) for _ in range(4)]

    selected = [set(round_stats["method_ids"]) for round_stats in rounds]
    assert all(selected[index].isdisjoint(selected[index + 1]) for index in range(3))
    assert len(set().union(*selected)) == 12


def test_duplicate_ids_are_rejected() -> None:
    methods = _methods()
    methods[1]["id"] = methods[0]["id"]

    with pytest.raises(ValueError, match="duplicado"):
        LotteryEngine.from_methods(methods)


def test_default_paths_are_packaged_and_machine_independent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert default_methods_file().is_file()
    assert default_methods_file().name == "library_combined.json"
    assert default_output_dir() == tmp_path / "CRIBA-Blackforge" / "lottery_results"


def test_run_lottery_writes_to_explicit_output_directory(tmp_path: Path) -> None:
    methods_file = tmp_path / "methods.json"
    output_dir = tmp_path / "results with spaces"
    methods_file.write_text(json.dumps(_methods()), encoding="utf-8")

    summary = run_lottery(
        str(methods_file),
        rounds=1,
        batch_size=2,
        mode="pure",
        seed=3,
        output_dir=output_dir,
    )

    assert summary["output_dir"] == str(output_dir)
    assert (
        json.loads((output_dir / "round_history.json").read_text(encoding="utf-8"))[0][
            "mode"
        ]
        == "pure"
    )


def test_cli_lottery_output_is_compatible_with_windows_cp1252(tmp_path: Path) -> None:
    methods_file = tmp_path / "methods.json"
    output_dir = tmp_path / "results"
    methods_file.write_text(json.dumps(_methods()), encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "cp1252"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "criba.cli",
            "lottery",
            "--methods-file",
            str(methods_file),
            "--output-dir",
            str(output_dir),
            "--mode",
            "associative",
            "--query",
            "tema especial β",
            "--rounds",
            "1",
            "--batch-size",
            "2",
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="cp1252",
        env=env,
    )

    assert "DOBLE LOTERIA DE CRIBA" in completed.stdout
    assert (output_dir / "round_history.json").is_file()
