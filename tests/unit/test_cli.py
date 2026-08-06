"""CLI boundary regression tests for CRIBA activation and prompt output."""
from __future__ import annotations

import json

from criba.cli import main
from criba.storage import Storage


QUERY = "Evaluar un flujo reversible de aprobación con trazabilidad Unicode: áβ"


def test_activate_preserves_query_and_persists_packet(tmp_path, capsys) -> None:
    database = tmp_path / "cli.sqlite3"

    result = main(["--database", str(database), "activate", "--query", QUERY])

    assert result == 0
    packet = json.loads(capsys.readouterr().out)
    assert packet["original_query"] == QUERY
    assert packet["packet_type"] == "MANDATORY_MODEL_PACKET"
    persisted = Storage(database).get(packet["activation_id"])
    assert persisted["query"] == QUERY
    assert persisted["packet"]["activation_id"] == packet["activation_id"]


def test_build_prompt_reads_file_and_writes_output(tmp_path, capsys) -> None:
    query_path = tmp_path / "query.txt"
    output_path = tmp_path / "prompt.md"
    database = tmp_path / "prompt.sqlite3"
    query_path.write_text(QUERY, encoding="utf-8")

    result = main([
        "--database",
        str(database),
        "build-prompt",
        "--file",
        str(query_path),
        "--output",
        str(output_path),
    ])

    assert result == 0
    assert capsys.readouterr().out == ""
    prompt = output_path.read_text(encoding="utf-8")
    assert "# Consulta original" in prompt
    assert QUERY in prompt
    assert "# MANDATORY_MODEL_PACKET" in prompt


def test_activate_without_query_returns_controlled_error(tmp_path, capsys) -> None:
    result = main(["--database", str(tmp_path / "invalid.sqlite3"), "activate"])

    captured = capsys.readouterr()
    assert result == 2
    assert captured.out == ""
    assert "Indica --query o --file" in captured.err


def test_blackforge_cli_runs_the_headless_pipeline(capsys) -> None:
    query = "Ejecutar BLACKFORGE desde la interfaz de línea de comandos: áβ"

    result = main([
        "blackforge",
        "--query",
        query,
        "--seed",
        "11",
        "--session-id",
        "cli-regression",
    ])

    assert result == 0
    packet = json.loads(capsys.readouterr().out)
    assert packet["status"] == "OK"
    assert packet["query"] == query
    assert packet["session_id"] == "cli-regression"
    assert packet["selection"]["selected_count"] == 12
    assert packet["ideas"]


def test_lottery_cli_uses_packaged_catalog_and_explicit_output_dir(
    tmp_path, capsys
) -> None:
    output_dir = tmp_path / "lottery results"

    result = main([
        "lottery",
        "--mode",
        "optimized",
        "--rounds",
        "1",
        "--batch-size",
        "2",
        "--seed",
        "19",
        "--output-dir",
        str(output_dir),
    ])

    assert result == 0
    assert "Modo: optimized" in capsys.readouterr().out
    history = json.loads(
        (output_dir / "round_history.json").read_text(encoding="utf-8")
    )
    assert history[0]["mode"] == "optimized"
