"""Regresiones de atribución: datos sintéticos, sin validar ideas reales."""
import json
from copy import deepcopy

import pytest

from criba.supra_dossier import (
    guardar_dossier, lecciones_previas, preparar_dossier, registrar_resultado,
)


def dossier(mechanism="MECANISMO_ANTERIOR"):
    return preparar_dossier({"candidate_id": "candidate-repetido", "run_id": "r1",
                            "mecanismo": mechanism}, "reducir cola de atencion")


def write_legacy(directory, records):
    path = directory / "dossiers.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return path


def observed(d):
    return {"tipo": "resultado_observado", "dossier_id": d["dossier_id"],
            "resultado": "positivo", "condiciones": "DATOS SINTETICOS"}


def test_each_preparation_has_own_identity():
    a, b = dossier(), dossier()
    assert a["dossier_id"] != b["dossier_id"]
    assert a["candidate_id"] == b["candidate_id"] == "candidate-repetido"
    assert a["run_id"] == b["run_id"] == "r1"


def test_positive_does_not_migrate_to_new_mechanism(tmp_path):
    a, b = dossier(), dossier("MECANISMO_NUEVO")
    guardar_dossier(a, tmp_path)
    registrar_resultado(a["dossier_id"], "positivo", directory=tmp_path)
    guardar_dossier(b, tmp_path)
    lessons = " ".join(lecciones_previas("atencion", tmp_path))
    assert "MECANISMO_ANTERIOR" in lessons
    assert "MECANISMO_NUEVO" not in lessons


@pytest.mark.parametrize("field", ["mecanismo", "problema", "prueba_discriminante"])
def test_conflicting_save_preserves_bytes(tmp_path, field):
    a = dossier()
    path = guardar_dossier(a, tmp_path)
    before = path.read_bytes()
    b = deepcopy(a)
    b[field] = "contexto modificado"
    with pytest.raises(ValueError):
        guardar_dossier(b, tmp_path)
    assert path.read_bytes() == before


def test_legacy_ambiguity_never_clears_and_other_history_survives(tmp_path):
    a, valid = dossier(), dossier("MECANISMO_VALIDO")
    a["dossier_id"], valid["dossier_id"] = "legacy-conflict", "legacy-valid"
    b = {**a, "mecanismo": "MECANISMO_NUEVO"}
    path = write_legacy(tmp_path, [a, observed(a), b, a, valid, observed(valid)])
    before = path.read_bytes()
    with pytest.warns(RuntimeWarning, match="ambigu"):
        lessons = lecciones_previas("atencion", tmp_path)
    assert len(lessons) == 1 and "MECANISMO_VALIDO" in lessons[0]
    assert path.read_bytes() == before


def test_legacy_reexport_only_timestamp_change_is_unambiguous(tmp_path):
    a = dossier()
    write_legacy(tmp_path, [a, observed(a), {**a, "creado_at": "otro instante"}])
    lessons = lecciones_previas("atencion", tmp_path)
    assert len(lessons) == 1 and "MECANISMO_ANTERIOR" in lessons[0]


def test_orphan_result_cannot_be_recorded(tmp_path):
    with pytest.raises(ValueError):
        registrar_resultado("no-existe", "positivo", directory=tmp_path)
    assert not (tmp_path / "dossiers.jsonl").exists()


def test_legacy_conflict_blocks_resave_and_result(tmp_path):
    a = dossier()
    path = write_legacy(tmp_path, [a, {**a, "problema": "otro problema"}, a])
    before = path.read_bytes()
    with pytest.raises(ValueError):
        guardar_dossier(a, tmp_path)
    with pytest.raises(ValueError):
        registrar_resultado(a["dossier_id"], "positivo", directory=tmp_path)
    assert path.read_bytes() == before


def test_malformed_orphan_and_nonobject_rows_do_not_create_lessons(tmp_path):
    path = write_legacy(tmp_path, [None, [], 42, {"dossier_id": ""},
                                  observed({"dossier_id": "no-existe"})])
    with path.open("a", encoding="utf-8") as handle:
        handle.write("{partial\n")
    assert lecciones_previas("", tmp_path) == []


def test_identical_save_is_idempotent(tmp_path):
    a = dossier()
    path = guardar_dossier(a, tmp_path)
    before = path.read_bytes()
    guardar_dossier({**a, "creado_at": "otra fecha"}, tmp_path)
    assert path.read_bytes() == before
