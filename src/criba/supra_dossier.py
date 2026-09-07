"""Dossier de avance tipo SUPRA (astra!.txt paso 4) — sin ejecutar SUPRA.

Contrato de exportación versionado: un candidato seleccionado se convierte en
un dossier con PRUEBA DISCRIMINANTE — la observación que haría abandonar la
propuesta o cambiar su mecanismo ANTES de construir un prototipo costoso.

Regla de honestidad (megaprompt §7, SUPRA): sin experimento ejecutado el
estado es ``SUPRA_EJECUCION_PENDIENTE`` — NUNCA PASS. El resultado observado
se registra aparte y alimenta ``lecciones_previas`` (paso 5: aprendizaje sobre
mecanismos y condiciones), cerrando el circuito con trazabilidad.
"""
from __future__ import annotations

import json
import os
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def _dossiers_dir(override: Path | None = None) -> Path:
    if override is not None:
        return override
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "CRIBA-Blackforge"
    return base / "dossiers"


def _contexto(dossier: dict[str, Any]) -> dict[str, Any]:
    """La fecha de reexportación no cambia el contenido del experimento."""
    return {k: v for k, v in dossier.items() if k not in ("creado_at", "dossier_id")}


def _leer_historial(
    path: Path,
) -> tuple[dict[str, dict[str, Any]], set[str], list[dict[str, Any]]]:
    dossiers: dict[str, dict[str, Any]] = {}
    ambiguos: set[str] = set()
    resultados: list[dict[str, Any]] = []
    if not path.exists():
        return dossiers, ambiguos, resultados
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict):
            continue
        identity = rec.get("dossier_id")
        if not isinstance(identity, str) or not identity.strip():
            continue
        if rec.get("tipo") == "resultado_observado":
            resultados.append(rec)
            continue
        if identity in dossiers and _contexto(dossiers[identity]) != _contexto(rec):
            ambiguos.add(identity)
        else:
            dossiers.setdefault(identity, rec)
    return dossiers, ambiguos, resultados


def preparar_dossier(
    entry: dict[str, Any],
    problema: str,
    *,
    ficha_bloqueo: dict[str, Any] | None = None,
    alternativa_explicativa: str = "",
) -> dict[str, Any]:
    """Dossier con prueba discriminante para un candidato PROPUESTA.

    ``alternativa_explicativa``: la otra explicación que la observación debe
    distinguir. Si no se aporta, el dossier lo declara en lugar de inventarla.
    """
    bloqueo = (ficha_bloqueo or {})
    prueba = {
        "afirmacion_decisiva": str(entry.get("prueba_concreta", ""))[:600],
        "alternativa_explicativa": alternativa_explicativa.strip(),
        "comparacion": (
            "observación que distinga el mecanismo propuesto de la alternativa; "
            "si no hay alternativa declarada, la prueba solo puede confirmar "
            "coherencia, no decidir entre explicaciones"
        ),
        "metrica": "",
        "resultado_favorable_mecanismo": "",
        "resultado_favorable_alternativa": "",
        "condicion_fracaso": "si la observación no discrimina, el dossier no decide",
        "coste_permisos": "a evaluar por el responsable antes de ejecutar",
        "estado_prueba": "NO_EJECUTADA",
    }
    return {
        "dossier_id": f"dossier-{uuid4().hex}",
        "candidate_id": entry.get("candidate_id", ""),
        "run_id": entry.get("run_id", ""),
        "problema": problema[:400],
        "bloqueo": bloqueo.get("bloqueo", ""),
        "origen_bloqueo": bloqueo.get("origen_bloqueo", ""),
        "hipotesis": str(entry.get("hipotesis", ""))[:800],
        "mecanismo": str(entry.get("mecanismo", "")),
        "evidencia_utilizada": list(entry.get("evidencia_local_usada", [])),
        "prueba_discriminante": prueba,
        "supuestos": list(entry.get("supuestos", [])),
        "estado": "SUPRA_EJECUCION_PENDIENTE",
        "creado_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def guardar_dossier(dossier: dict[str, Any], directory: Path | None = None) -> Path:
    directory = _dossiers_dir(directory)
    path = directory / "dossiers.jsonl"
    identity = dossier.get("dossier_id")
    if not isinstance(identity, str) or not identity.strip():
        raise ValueError("dossier_id es obligatorio")
    if dossier.get("tipo") == "resultado_observado":
        raise ValueError("usar registrar_resultado para observaciones")
    existentes, ambiguos, _ = _leer_historial(path)
    if identity in ambiguos or (
        identity in existentes and _contexto(existentes[identity]) != _contexto(dossier)
    ):
        raise ValueError("dossier_id ambiguo: crear un dossier nuevo para cambiar su contenido")
    if identity in existentes:
        return path
    directory.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dossier, ensure_ascii=False) + "\n")
    return path


def registrar_resultado(
    dossier_id: str,
    resultado: str,
    *,
    condiciones: str = "",
    directory: Path | None = None,
) -> dict[str, Any]:
    """Registra el resultado OBSERVADO de la prueba discriminante.

    ``resultado`` debe ser uno de: positivo | negativo | indeterminado.
    Un fallo de datos/proveedor/implementación no atribuye efecto al
    mecanismo (ASTRA §7): por eso existe ``indeterminado``.
    """
    if resultado not in ("positivo", "negativo", "indeterminado"):
        raise ValueError("resultado debe ser positivo|negativo|indeterminado")
    directory = _dossiers_dir(directory)
    path = directory / "dossiers.jsonl"
    dossiers, ambiguos, _ = _leer_historial(path)
    if dossier_id not in dossiers or dossier_id in ambiguos:
        raise ValueError("el resultado requiere un dossier existente y no ambiguo")
    registro = {
        "dossier_id": dossier_id,
        "resultado": resultado,
        "condiciones": condiciones[:400],
        "registrado_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "autor": "humano/experimento",  # solo experimentos observados escriben aquí
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(
            {**registro, "tipo": "resultado_observado"}, ensure_ascii=False) + "\n")
    return registro


def lecciones_previas(query: str, directory: Path | None = None, limit: int = 3) -> list[str]:
    """Lecciones registradas pertinentes a la consulta (paso 5 del circuito).

    Un resultado observado vuelve a la búsqueda como aprendizaje trazable:
    'este cambio de mecanismo produjo este resultado en estas condiciones'.
    """
    path = _dossiers_dir(directory) / "dossiers.jsonl"
    if not path.exists() or limit <= 0:
        return []
    q = (query or "").casefold()
    dossiers, ambiguos, resultados = _leer_historial(path)
    if ambiguos:
        warnings.warn(
            "Historial ambiguo: resultados excluidos del aprendizaje; registros conservados",
            RuntimeWarning,
            stacklevel=2,
        )
    out: list[str] = []
    for res in resultados:
        identity = res.get("dossier_id", "")
        if identity in ambiguos or identity not in dossiers:
            continue
        if res.get("resultado") not in ("positivo", "negativo", "indeterminado"):
            continue
        d = dossiers[identity]
        problema = str(d.get("problema", "")).casefold()
        if q and not any(w in problema for w in q.split() if len(w) >= 4):
            continue
        out.append(
            f"{res['dossier_id']}: prueba discriminante {res['resultado']} "
            f"para '{str(d.get('mecanismo', ''))[:120]}' "
            f"(condiciones: {res.get('condiciones', '')[:120]})"
        )
        if len(out) >= limit:
            break
    return out
