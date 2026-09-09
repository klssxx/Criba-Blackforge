"""Rescate de ideas fallidas por complementariedad (BLUEPRINT §5, propuesta astra).

Hipótesis de diseño (a probar, NO invención inédita declarada): dos propuestas
que FALLAN por separado pueden complementarse — una produce el recurso que la
otra necesita, o transforma la condición que bloqueaba a la primera. El valor
está en las INTERACCIONES, no solo en las técnicas individuales.

Cuatro movimientos (paste_13):
1. CONSERVAR EL FRACASO CON PRECISIÓN: una idea descartada deja una relación
   verificable — «este mecanismo sería útil, pero falla porque necesita X; si X
   cambiara de esta manera, merecería volver a probarse». No se guarda «es mala
   idea»; se guarda QUÉ condición la bloquea.
2. BUSCAR LA PIEZA QUE TRANSFORMA ESE BLOQUEO: otra propuesta cuyo mecanismo
   elimina, reduce o transforma la condición de fracaso.
3. EXIGIR QUE EL CRUCE TENGA CONSECUENCIAS: probar A sola, B sola y A+B, con
   igual presupuesto. La combinación SOLO se conserva si supera a AMBAS bajo la
   misma prueba — si produce el mismo comportamiento con explicación más larga,
   se descarta.
4. BUSCAR EL EXPERIMENTO DONDE LAS PROPUESTAS DISCREPAN: cuando dos parezcan
   igualmente buenas, proponer la situación en que predicen resultados
   diferentes.

Reglas de honestidad (mismo patrón que outcome_store / off_policy):
- Determinista y offline: sin modelo, sin red. La COMPROBACIÓN de que A+B supera
  a A y a B es una función inyectable (``evaluador``); sin ella el veredicto es
  UNRESOLVED honesto, nunca un RESCUED fabricado.
- Una combinación solo se declara RESCUED si la evidencia la supera a ambas
  componentes POR SEPARADO bajo el mismo evaluador.
- El bloqueo conservado es texto estructurado, no una etiqueta vaga.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

# Evaluador inyectable: (mecanismo, contexto) -> puntuación comparable [0,1].
# Debe ser DETERMINISTA para la reproducibilidad del veredicto. Sin ella, toda
# comprobación es UNRESOLVED (nunca se fabrica un rescate).
Evaluador = Callable[[str, str], float]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _default_rescate_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    return base / "CRIBA-Blackforge" / "rescate" / "bloqueos.jsonl"


@dataclass(frozen=True)
class Bloqueo:
    """Movimiento 1: el fracaso conservado con precisión, no como etiqueta vaga.

    ``condicion`` es lo que el mecanismo NECESITA y no tiene (X). ``cambio`` es
    cómo debería cambiar X para que mereciera volver a probarse. Ambos son
    texto estructurado y comprobable — nunca «no funciona» a secas.
    """

    idea_id: str
    mecanismo: str
    condicion: str          # lo que necesita y no tiene (X)
    cambio: str             # cómo debería cambiar X para reintentar
    evidencia_fallo: str = ""
    recorded_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if not d["recorded_at"]:
            d["recorded_at"] = _now_iso()
        return d


@dataclass(frozen=True)
class Complemento:
    """Movimiento 2: una propuesta cuyo mecanismo podría transformar el bloqueo."""

    idea_id: str
    mecanismo: str
    transforma: str         # qué condición elimina/reduce/transforma


@dataclass(frozen=True)
class VeredictoRescate:
    """Resultado auditable de probar A sola, B sola y A+B."""

    bloqueo_id: str
    complemento_id: str
    score_a: float | None
    score_b: float | None
    score_ab: float | None
    verdict: str            # RESCUED | NOT_RESCUED | UNRESOLVED
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def append_bloqueo(path: Path | str, bloqueo: Bloqueo) -> None:
    """Movimiento 1: conserva el fracaso (append-only, auditable)."""
    if not bloqueo.condicion.strip() or not bloqueo.cambio.strip():
        raise ValueError("un bloqueo exige condicion y cambio estructurados (no etiqueta vaga)")
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(bloqueo.to_dict(), ensure_ascii=False) + "\n")


def read_bloqueos(path: Path | str) -> list[Bloqueo]:
    p = Path(path)
    if not p.exists():
        return []
    out: list[Bloqueo] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
            out.append(Bloqueo(
                idea_id=str(rec["idea_id"]), mecanismo=str(rec["mecanismo"]),
                condicion=str(rec["condicion"]), cambio=str(rec["cambio"]),
                evidencia_fallo=str(rec.get("evidencia_fallo", "")),
                recorded_at=str(rec.get("recorded_at", "")),
            ))
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    return out


def bloqueos_hash(path: Path | str) -> str:
    p = Path(path)
    if not p.exists():
        return hashlib.sha256(b"").hexdigest()
    return hashlib.sha256(p.read_bytes()).hexdigest()


def probar_rescate(
    bloqueo: Bloqueo,
    complemento: Complemento,
    evaluador: Evaluador | None,
    *,
    contexto: str = "",
) -> VeredictoRescate:
    """Movimiento 3: prueba A sola, B sola y A+B con el MISMO evaluador.

    Veredictos:
    - RESCUED: A+B supera a A Y a B (la interacción aporta capacidad nueva).
    - NOT_RESCUED: A+B NO supera a alguna componente (misma conducta con
      explicación más larga -> se descarta, honesto).
    - UNRESOLVED: sin evaluador (no hay prueba) o la puntuación no es finita.
    """
    if evaluador is None:
        return VeredictoRescate(
            bloqueo_id=bloqueo.idea_id, complemento_id=complemento.idea_id,
            score_a=None, score_b=None, score_ab=None,
            verdict="UNRESOLVED",
            reason="sin evaluador: no hay prueba que ejecutar (nunca se fabrica un rescate)",
        )
    mecanismo_a = bloqueo.mecanismo
    mecanismo_b = complemento.mecanismo
    mecanismo_ab = f"{mecanismo_a} + {mecanismo_b} [{complemento.transforma} -> {bloqueo.condicion}]"
    try:
        score_a = float(evaluador(mecanismo_a, contexto))
        score_b = float(evaluador(mecanismo_b, contexto))
        score_ab = float(evaluador(mecanismo_ab, contexto))
    except Exception as exc:  # noqa: BLE001 — un fallo del evaluador es UNRESOLVED
        return VeredictoRescate(
            bloqueo_id=bloqueo.idea_id, complemento_id=complemento.idea_id,
            score_a=None, score_b=None, score_ab=None,
            verdict="UNRESOLVED", reason=f"evaluador falló: {exc}",
        )
    for s in (score_a, score_b, score_ab):
        if not (0.0 <= s <= 1.0):
            return VeredictoRescate(
                bloqueo_id=bloqueo.idea_id, complemento_id=complemento.idea_id,
                score_a=score_a, score_b=score_b, score_ab=score_ab,
                verdict="UNRESOLVED", reason=f"puntuación fuera de [0,1]: {s}",
            )
    if score_ab > score_a and score_ab > score_b:
        return VeredictoRescate(
            bloqueo_id=bloqueo.idea_id, complemento_id=complemento.idea_id,
            score_a=score_a, score_b=score_b, score_ab=score_ab,
            verdict="RESCUED",
            reason=(
                f"A+B ({score_ab:.3f}) supera a A ({score_a:.3f}) y a B ({score_b:.3f}): "
                f"la interacción aporta capacidad que ninguna tenía por separado"
            ),
        )
    return VeredictoRescate(
        bloqueo_id=bloqueo.idea_id, complemento_id=complemento.idea_id,
        score_a=score_a, score_b=score_b, score_ab=score_ab,
        verdict="NOT_RESCUED",
        reason=(
            f"A+B ({score_ab:.3f}) no supera a A ({score_a:.3f}) y/o B ({score_b:.3f}): "
            f"misma conducta con explicación más larga, se descarta"
        ),
    )


def buscar_complementos(
    bloqueo: Bloqueo,
    candidatos: Sequence[Complemento],
    evaluador: Evaluador | None,
    *,
    contexto: str = "",
) -> list[VeredictoRescate]:
    """Movimiento 2+3: para cada candidato, prueba si transforma el bloqueo.

    Devuelve los veredictos ordenados por score_ab descendente (UNRESOLVED al
    final). Nunca fabrica un complemento: solo evalúa los dados.
    """
    veredictos = [
        probar_rescate(bloqueo, c, evaluador, contexto=contexto) for c in candidatos
    ]
    def _key(v: VeredictoRescate) -> float:
        return v.score_ab if v.score_ab is not None else -1.0
    return sorted(veredictos, key=_key, reverse=True)
