"""CLI boundary regression tests for CRIBA activation and prompt output."""
from __future__ import annotations

import json

from criba import cli
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


def test_blackforge_cli_uses_shared_profile_and_reasoning_override(
    tmp_path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("CRIBA_MODEL_CONFIG", str(tmp_path / "models.json"))
    seen: dict[str, object] = {}

    def enhance(query, ideas, *, product, settings):
        seen.update(
            query=query,
            product=product,
            reasoning=settings.active_profile().reasoning,
        )
        enhanced = [dict(idea) for idea in ideas]
        enhanced[0]["title"] = "Propuesta redactada por el modelo local"
        return enhanced, {"status": "ok", "enhanced_count": 1}

    monkeypatch.setattr(cli, "enhance_ideas_with_model", enhance)
    result = main(
        [
            "blackforge",
            "--query",
            "Reducir fraude",
            "--seed",
            "11",
            "--use-configured-model",
            "--reasoning",
            "deep",
        ]
    )

    packet = json.loads(capsys.readouterr().out)
    assert result == 0
    assert seen == {
        "query": "Reducir fraude",
        "product": "BLACKFORGE",
        "reasoning": "deep",
    }
    assert packet["ideas"][0]["title"] == "Propuesta redactada por el modelo local"
    assert packet["semantic_generation"]["status"] == "ok"


def test_cli_rejects_legacy_and_shared_model_flags_together(tmp_path, capsys) -> None:
    result = main(
        [
            "--database",
            str(tmp_path / "conflict.sqlite3"),
            "activate",
            "--query",
            "Reducir fraude",
            "--use-configured-model",
            "--llm",
            "offline",
        ]
    )

    captured = capsys.readouterr()
    assert result == 2
    assert "Elige --use-configured-model o --llm" in captured.err


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


def test_tecnicas_routes_canon_with_traceability(capsys) -> None:
    """El router del canon T001-T130 es consumible por CLI (solo lectura).
    Técnicas restauradas (canon 2026-09-08.1): tarea relevante selecciona
    ejecutables reales y las PLANNED quedan como brechas."""
    result = main(["tecnicas", "análisis morfológico y escenarios contrafactuales",
                   "--max", "3"])

    assert result == 0
    routing = json.loads(capsys.readouterr().out)
    assert routing["canon_version"]
    assert routing["provenance"]["generator"].endswith("gen_registry.py")
    selected_ids = [t["id"] for t in routing["selected"]]
    assert "T059" in selected_ids and "T129" in selected_ids
    assert all(t["executable"] for t in routing["selected"])
    for gap in routing["coverage_gaps"]:
        assert gap["reasons"][-1].startswith("no_implementada")


def test_tecnicas_blackforge_profile_changes_order(capsys) -> None:
    result = main(["tecnicas", "señales y escenarios adversariales", "--perfil", "BLACKFORGE"])

    assert result == 0
    routing = json.loads(capsys.readouterr().out)
    assert routing["profile"] == "BLACKFORGE"
    adversarial = [t["id"] for t in (*routing["selected"], *routing["coverage_gaps"])
                   if "ADVERSARIAL" in json.dumps(t)]
    assert adversarial


def test_tecnicas_invalid_max_returns_controlled_error(capsys) -> None:
    """qa P3-2: --max 0 es error del llamador, no una selección vacía silenciosa."""
    result = main(["tecnicas", "análisis morfológico", "--max", "0"])

    captured = capsys.readouterr()
    assert result == 2
    assert captured.out == ""
    assert "Error:" in captured.err
    assert "max_techniques" in captured.err


def test_tecnicas_invalid_max_per_family_returns_controlled_error(capsys) -> None:
    result = main(["tecnicas", "análisis morfológico", "--max-por-familia", "0"])

    captured = capsys.readouterr()
    assert result == 2
    assert captured.out == ""
    assert "Error:" in captured.err
    assert "max_per_family" in captured.err


def test_tecnicas_corrupt_registry_entry_returns_controlled_error(
    tmp_path, monkeypatch, capsys
) -> None:
    """qa P2-2: una entrada no-mapping en `techniques` era AttributeError crudo
    con traceback; ahora el CLI la convierte en Error + exit 2."""
    import yaml

    from criba import constants

    monkeypatch.setattr(constants, "DATA_ROOT", tmp_path)
    registry_dir = tmp_path / "intelligence"
    registry_dir.mkdir()
    raw = {
        "schema_version": 2,
        "canon_version": "corrupt.1",
        "provenance": {"source": "s", "generator": "g", "parts": ["p"]},
        "techniques": ["foo"],
    }
    (registry_dir / "technique_registry.yaml").write_text(
        yaml.safe_dump(raw), encoding="utf-8"
    )

    result = main(["tecnicas", "morfologico"])

    captured = capsys.readouterr()
    assert result == 2
    assert captured.out == ""
    assert "Error: technique entry 0 must be a mapping" in captured.err


def test_tecnicas_incomplete_provenance_returns_controlled_error(
    tmp_path, monkeypatch, capsys
) -> None:
    """qa P2-1: provenance {} ya no carga en silencio; el CLI reporta el fallo."""
    import yaml

    from criba import constants

    monkeypatch.setattr(constants, "DATA_ROOT", tmp_path)
    registry_dir = tmp_path / "intelligence"
    registry_dir.mkdir()
    raw = {
        "schema_version": 2,
        "canon_version": "corrupt.1",
        "provenance": {},
        "techniques": [],
    }
    (registry_dir / "technique_registry.yaml").write_text(
        yaml.safe_dump(raw), encoding="utf-8"
    )

    result = main(["tecnicas", "morfologico"])

    captured = capsys.readouterr()
    assert result == 2
    assert "Error:" in captured.err
    assert "provenance" in captured.err


# ---------------------------------------------------------------------------
# Ejecución de técnicas desde el producto (§82 completo: canon→router→
# resolver→operador→salida, accesible por CLI). El canon decide ejecutabilidad.
# ---------------------------------------------------------------------------

def test_tecnicas_ejecuta_t059_con_parametros_canonicos(tmp_path, capsys) -> None:
    entrada = tmp_path / "entrada.json"
    entrada.write_text(json.dumps({
        "params": {"dimensions": {"motor": ["eléctrico", "combustión"],
                                  "frenado": ["regenerativo", "fricción"]}},
    }), encoding="utf-8")

    result = main(["tecnicas", "análisis morfológico", "--ejecutar", "T059",
                   "--problema", "vehículo urbano", "--entrada", str(entrada)])

    assert result == 0
    outcome = json.loads(capsys.readouterr().out)
    assert outcome["technique"] == "T059"
    assert outcome["canon_version"]
    assert outcome["results"], "el análisis morfológico debe producir hipótesis"
    for candidate in outcome["results"]:
        assert "T059" in candidate["operators"], "trazabilidad de operador exigida"


def test_tecnicas_ejecuta_t053_con_evidencia_de_entrada(tmp_path, capsys) -> None:
    docs = [{"title": f"doc{i}", "metadata": {"concepts": ["a", "b"] if i % 2 else ["b", "c"]}}
            for i in range(8)]
    docs += [{"title": "raro", "metadata": {"concepts": ["zzz", "yyy"]}}]
    entrada = tmp_path / "docs.json"
    entrada.write_text(json.dumps(docs), encoding="utf-8")

    result = main(["tecnicas", "combinaciones raras", "--ejecutar", "T053",
                   "--entrada", str(entrada)])

    assert result == 0
    outcome = json.loads(capsys.readouterr().out)
    assert len(outcome["evidence_doc_ids"]) == 9


def test_tecnicas_ejecuta_t059_sin_entrada_da_error_controlado(capsys) -> None:
    result = main(["tecnicas", "x", "--ejecutar", "T059", "--problema", "p"])

    captured = capsys.readouterr()
    assert result == 2
    assert "dimensions" in captured.err


def test_tecnicas_rechaza_ejecutar_planeada(capsys) -> None:
    """Negativo §82: el canon no autoriza ejecutar una PLANNED."""
    result = main(["tecnicas", "curvas de sustitución", "--ejecutar", "T130"])

    captured = capsys.readouterr()
    assert result == 2
    assert "PLANNED" in captured.err
    assert "canon" in captured.err


def test_tecnicas_rechaza_ejecutar_desconocida(capsys) -> None:
    result = main(["tecnicas", "x", "--ejecutar", "T999"])

    captured = capsys.readouterr()
    assert result == 2
    assert "desconocida" in captured.err
