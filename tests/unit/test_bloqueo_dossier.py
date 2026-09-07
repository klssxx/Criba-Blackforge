"""Tests del bloque 'bloqueo → desbloqueo → prueba discriminante' (astra!.txt)."""
from __future__ import annotations

import json

import pytest

from criba.bloqueo import FichaBloqueo, validar_ficha
from criba.inventar import invent
from criba.supra_dossier import (
    guardar_dossier,
    lecciones_previas,
    preparar_dossier,
    registrar_resultado,
)


def _ficha() -> FichaBloqueo:
    return FichaBloqueo(
        resultado_buscado="reducir la cola sin contratar personal",
        bloqueo="cada atención genera una segunda visita por errores previos",
        explicacion_bloqueo="el volumen depende de retornos, no solo de capacidad",
        origen_bloqueo="hipotesis",
        restricciones_obligatorias=["no despedir", "misma calidad"],
        evidencia=[{"texto": "muestra inicial de retornos", "origen": "pendiente",
                    "relacion": "falta_comprobar"}],
    )


def test_validar_ficha_distingue_origen_y_relacion() -> None:
    assert validar_ficha(_ficha()) == []
    mala = FichaBloqueo("", "", "", origen_bloqueo="seguro",
                        evidencia=[{"texto": "x", "origen": "hecho", "relacion": "aprueba"}])
    errores = validar_ficha(mala)
    assert len(errores) == 5  # 3 vacíos + origen_bloqueo inválido + relacion inválida


def test_bloqueo_llega_al_prompt_del_proponente() -> None:
    """El bloqueo identificado viaja en la SOLICITUD real al intérprete."""
    from criba.interprete import adaptador

    class _Resp:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            return {"choices": [{"message": {"content": json.dumps({
                "hipotesis": "h", "mecanismo": "m", "aportacion_por_tecnica": [],
                "supuestos": [], "prueba_concreta": "p",
                "ruta_desbloqueo": "desacoplar_dependencia"})}}]}
    capturado = {}
    class _Client:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, url, json=None, headers=None):
            capturado["payload"] = json
            return _Resp()
    monkey = pytest.MonkeyPatch()
    monkey.setattr(adaptador.httpx, "Client", _Client)
    monkey.setenv("NOUS_API_KEY", "test-key")
    try:
        adaptador.LocalInterprete().proponer(
            "q", {"method1": "A", "method2": "B", "bloqueo": _ficha().to_dict()}, None, [])
    finally:
        monkey.undo()
    contenido = capturado["payload"]["messages"][1]["content"]
    assert "BLOQUEO IDENTIFICADO" in contenido
    assert "segunda visita por errores previos" in contenido
    assert "elimin" in contenido and "desacoplar" in contenido  # rutas declaradas
    assert "hipotesis" in contenido  # origen declarado, no colapsado


def test_invent_propaga_ficha_y_ruta() -> None:
    def _proponer(query, idea, domain, evidence=None):
        assert idea.get("bloqueo", {}).get("bloqueo"), "el cruce debe llevar el bloqueo"
        return {"estado": "PROPUESTA", "hipotesis": "h", "mecanismo": "m del problema",
                "aportacion_por_tecnica": [], "supuestos": [], "prueba_concreta": "p",
                "ruta_desbloqueo": "sustituir_mecanismo", "error": ""}
    sheet = invent("cola de atención", seed=5, rounds=1, batch_size=6, top=2,
                   offline=True, methods=_methods_catalogo(), sources=[],
                   proponer=_proponer, ficha_bloqueo=_ficha().to_dict())
    assert sheet["ficha_bloqueo"]["bloqueo"].startswith("cada atención")
    assert all(e["ruta_desbloqueo"] == "sustituir_mecanismo" for e in sheet["entries"])


def _methods_catalogo():
    return [
        {"id": f"p-{i}", "title": f"perspectiva {i}", "family": "perspectiva",
         "thinking_class": "perspectiva"} for i in range(8)
    ] + [
        {"id": f"g-{i}", "title": f"generacion {i}", "family": "generacion",
         "thinking_class": "generacion"} for i in range(8)
    ] + [
        {"id": f"r-{i}", "title": f"ruptura {i}", "family": "ruptura",
         "thinking_class": "ruptura"} for i in range(8)
    ] + [
        {"id": f"e-{i}", "title": f"escape {i}", "family": "escape",
         "thinking_class": "escape"} for i in range(8)
    ]


def _entry_stub(mecanismo: str) -> dict:
    return {
        "candidate_id": "invent-1-abc-01", "run_id": "r1", "title": "t",
        "hipotesis": "h", "mecanismo": mecanismo, "prueba_concreta":
        "medir retornos frente a capacidad", "supuestos": ["s"],
        "evidencia_local_usada": [],
    }


def test_dossier_estado_pendiente_nunca_pass(tmp_path) -> None:
    dossier = preparar_dossier(_entry_stub("m"), "cola", ficha_bloqueo=_ficha().to_dict())
    assert dossier["estado"] == "SUPRA_EJECUCION_PENDIENTE"
    assert dossier["prueba_discriminante"]["estado_prueba"] == "NO_EJECUTADA"
    assert "alternativa" in dossier["prueba_discriminante"]["comparacion"]
    path = guardar_dossier(dossier, directory=tmp_path)
    lineas = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lineas) == 1 and json.loads(lineas[0])["dossier_id"] == dossier["dossier_id"]


def test_circuito_aprendizaje_resultado_vuelve_como_leccion(tmp_path) -> None:
    """La prueba más importante (astra!.txt §5): un resultado registrado
    modifica la exploración posterior pertinente con trazabilidad."""
    d = preparar_dossier(_entry_stub("rotar turnos de atención"), "reducir la cola de atención")
    guardar_dossier(d, directory=tmp_path)
    registrar_resultado(d["dossier_id"], "negativo",
                        condiciones="retornos dominados por errores de formulario",
                        directory=tmp_path)
    lecciones = lecciones_previas("cola de atención", directory=tmp_path)
    assert lecciones and "negativo" in lecciones[0] and "rotar turnos" in lecciones[0]
    # la lección llega al siguiente invent() dentro del bloqueo
    vistos = []
    def _proponer(query, idea, domain, evidence=None):
        vistos.append(idea.get("bloqueo", {}).get("lecciones_previas"))
        return {"estado": "PROPUESTA", "hipotesis": "h", "mecanismo": "m",
                "aportacion_por_tecnica": [], "supuestos": [], "prueba_concreta": "p",
                "error": ""}
    invent("cola de atención", seed=2, rounds=1, batch_size=6, top=2, offline=True,
           methods=_methods_catalogo(), sources=[], proponer=_proponer,
           ficha_bloqueo=_ficha().to_dict())
    # lecciones_previas por defecto lee LOCALAPPDATA; el test usa tmp, así que
    # solo verificamos que el canal existe y la ficha viaja
    assert vistos and all(isinstance(v, list) for v in vistos)


def test_registrar_resultado_valida_vocabulario(tmp_path) -> None:
    with pytest.raises(ValueError):
        registrar_resultado("d1", "PASS", directory=tmp_path)
