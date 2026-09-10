"""Memoria experimental técnica→outcome (BLUEPRINT §4.2, multiplicador fundamental).

Cierra el circuito: qué técnica/clase de pensamiento produjo qué resultado
observado, versionado por ``canon_version`` y consultable por el router como
prior UCB. La política de selección deja de ser congelada y pasa a aprender de
la propia experiencia del sistema.

Reglas de honestidad (patrón supra_dossier, ya probado):
- Append-only JSONL, validación de esquema por línea; las líneas malformadas se
  ignoran (nunca rompen el aprendizaje).
- El historial ambiguo se EXCLUYE del cálculo con RuntimeWarning (bytes intactos).
- Una PLANNED con prior alto NUNCA se vuelve ejecutable: el prior solo reordena
  candidatos ya elegibles; el canon sigue decidiendo qué es ejecutable.
- Sin red, sin modelo, determinista. El hash del store se expone para hacerlo
  comprobable (§15.2).

Señal compuesta etiquetada por fuente (§12.2.3): los canales verdict prior-art,
score del juez y resultado_observado se guardan por separado — nunca mezclados
en un solo número (no confundir calidad de generación con novedad).

REPRODUCIBILIDAD (contrato completo, no solo seed+hash): una consulta de prior
es reproducible SÍ Y SOLO SÍ se fijan los CUATRO factores:
  1. la semilla del consumidor (lotería/selector);
  2. el hash del store (mismo contenido);
  3. la FECHA de evaluación (el prior decae con HALF_LIFE_DAYS: mismo store,
     distinta fecha => distinto prior; pasar ``now`` explícito para fijarlo);
  4. la VERSIÓN de la política de prior (el algoritmo UCB/atenúa-negativos:
     cambia la salida aunque los tres anteriores sean idénticos).
Afirmar «mismo seed + mismo hash => mismo output» sin fijar fecha y política es
INCORRECTO y queda aquí desmentido explícitamente (hallazgo 5 de la auditoría).

AGREGADO DE FAMILIA (fuente de verdad): el back-off jerárquico lee registros
EXPLÍCITOS ``__family__`` escritos por record_family_outcome (inventar los
emite por cada clase). Los registros finos NO se agregan en lectura: si no hay
registro ``__family__`` explícito, no hay back-off. Cualquier documentación que
afirme lo contrario está desactualizada respecto a este código.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Canales de resultado admitidos, etiquetados por fuente (§12.2.3). Nunca se
# mezclan en un único número: cada prior se calcula sobre UN canal.
CHANNEL_VERDICT = "verdict"          # prior-art: SURVIVED/PARTIAL/UNRESOLVED
CHANNEL_JUDGE = "judge"              # crítica automática: score 0..1
CHANNEL_OBSERVED = "observed"        # dossier resultado_observado: pos/neg/indet

_VALID_OUTCOMES: dict[str, frozenset[str]] = {
    CHANNEL_VERDICT: frozenset({"SURVIVED_SEARCH", "PARTIAL_PRIOR_ART", "UNRESOLVED"}),
    CHANNEL_OBSERVED: frozenset({"positivo", "negativo", "indeterminado"}),
}

# Valor numérico por outcome, por canal. El juez ya es 0..1 y no se mapea.
_VERDICT_VALUE = {"SURVIVED_SEARCH": 1.0, "PARTIAL_PRIOR_ART": 0.5, "UNRESOLVED": 0.0}
_OBSERVED_VALUE = {"positivo": 1.0, "indeterminado": 0.5, "negativo": 0.0}

# Decaimiento temporal (§14.3): vida media fija y documentada. El reset por
# cambio de canon_epoch domina al decaimiento.
HALF_LIFE_DAYS: float = 90.0
# Back-off jerárquico (§12.2.1): una celda fina con menos observaciones que esto
# usa el prior del nivel agregado (familia).
BACKOFF_MIN_OBS = 3
# Nivel agregado al que se hace back-off cuando la celda fina no tiene datos.
_AGGREGATE_KEY = "__family__"


def _default_store_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    return base / "CRIBA-Blackforge" / "outcomes" / "technique_outcomes.jsonl"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class TechniqueOutcomeStore:
    """Store versionado y auditable de outcomes por (técnica, clase).

    Clave de celda fina: (profile, family, technique_id, channel). El back-off
    agrega por (profile, family, channel) usando technique_id == _AGGREGATE_KEY.
    """

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else _default_store_path()

    # -- escritura ---------------------------------------------------------
    def record(
        self,
        *,
        profile: str,
        family: str,
        technique_id: str,
        channel: str,
        outcome: str,
        canon_version: str,
        value: float | None = None,
        run_id: str = "",
        recorded_at: datetime | None = None,
    ) -> dict[str, Any]:
        """Registra un outcome observado. Validación de esquema estricta.

        ``value`` opcional fija el valor numérico (p. ej. score del juez 0..1);
        si se omite se deriva del outcome según el canal.
        """
        if channel not in (CHANNEL_VERDICT, CHANNEL_JUDGE, CHANNEL_OBSERVED):
            raise ValueError(f"canal desconocido: {channel}")
        if channel in _VALID_OUTCOMES and outcome not in _VALID_OUTCOMES[channel]:
            raise ValueError(f"outcome inválido para {channel}: {outcome}")
        if not technique_id.strip():
            raise ValueError("technique_id es obligatorio")
        if value is None:
            if channel == CHANNEL_VERDICT:
                value = _VERDICT_VALUE[outcome]
            elif channel == CHANNEL_OBSERVED:
                value = _OBSERVED_VALUE[outcome]
            else:
                raise ValueError("channel=judge requiere value explícito (score 0..1)")
        value = float(value)
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"value fuera de [0,1]: {value}")
        ts = (recorded_at or _now()).astimezone(timezone.utc)
        record = {
            "profile": profile,
            "family": family,
            "technique_id": technique_id,
            "channel": channel,
            "outcome": outcome,
            "value": value,
            "canon_version": canon_version,
            "run_id": run_id,
            "recorded_at": ts.isoformat(timespec="seconds"),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    # -- lectura -----------------------------------------------------------
    def _read_valid(self) -> list[dict[str, Any]]:
        """Lee y valida; el historial ambiguo se excluye con RuntimeWarning."""
        if not self.path.exists():
            return []
        valid: list[dict[str, Any]] = []
        malformed = 0
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if not isinstance(rec, dict):
                malformed += 1
                continue
            if not all(isinstance(rec.get(k), str) and rec.get(k) for k in
                       ("profile", "family", "technique_id", "channel", "outcome")):
                malformed += 1
                continue
            if not isinstance(rec.get("value"), (int, float)):
                malformed += 1
                continue
            valid.append(rec)
        if malformed:
            warnings.warn(
                f"OutcomeStore: {malformed} líneas malformadas excluidas del "
                "aprendizaje; registros conservados",
                RuntimeWarning,
                stacklevel=2,
            )
        return valid

    @staticmethod
    def _decay_weight(recorded_at: datetime | None, now: datetime) -> float:
        if recorded_at is None:
            return 1.0
        age_days: float = max(0.0, (now - recorded_at).total_seconds() / 86400.0)
        weight: float = 0.5 ** (age_days / HALF_LIFE_DAYS)
        return weight

    def _cell_stats(
        self,
        records: list[dict[str, Any]],
        *,
        profile: str,
        family: str,
        technique_id: str,
        channel: str,
        canon_version: str | None,
        now: datetime,
    ) -> tuple[float, int]:
        """Suma ponderada por decaimiento y n efectivo para UNA celda.

        P3 (idempotencia): una misma observación registrada varias veces NO
        cuenta como experimentos independientes. La identidad de observación es
        (technique_id, channel, run_id, outcome, value, canon_version): un
        reintento de escritura del MISMO resultado se deduplica contando UNA
        vez (la más reciente). Ensayos DISTINTOS del mismo run con distinto
        outcome sí cuentan por separado.

        El dedup SOLO se aplica a registros con ``run_id`` NO vacío: sin
        identidad de ensayo explícita, cada línea es una observación distinta
        (no se puede afirmar que sea un reintento — sería deduplicar ensayos
        legítimos).
        """
        wsum = 0.0
        n_eff = 0
        seen: dict[tuple[Any, ...], float] = {}  # identidad -> mejor peso (más reciente)
        for rec in records:
            if rec["profile"] != profile or rec["family"] != family:
                continue
            if rec["technique_id"] != technique_id or rec["channel"] != channel:
                continue
            if canon_version is not None and rec.get("canon_version") != canon_version:
                continue  # reset por canon_epoch (§13.4): épocas distintas no heredan
            w = self._decay_weight(_parse_ts(rec.get("recorded_at")), now)
            run_id = str(rec.get("run_id") or "")
            value = float(rec["value"])
            if not run_id:
                # sin identidad de ensayo: cada línea es una observación distinta
                wsum += w * value
                n_eff += 1
                continue
            identity = (
                rec["technique_id"], rec["channel"], run_id,
                rec["outcome"], round(value, 6), rec.get("canon_version"),
            )
            # dedup por identidad: conserva el peso MAYOR (el registro más
            # reciente domina al reintento más antiguo del mismo ensayo).
            if identity not in seen or w > seen[identity]:
                seen[identity] = w
        for value_key, w in ((k, v) for k, v in seen.items()):
            # value viene codificado en la identidad (posición 4)
            wsum += w * float(value_key[4])
            n_eff += 1
        return wsum, n_eff

    def prior(
        self,
        *,
        profile: str,
        family: str,
        technique_id: str,
        channel: str = CHANNEL_VERDICT,
        canon_version: str | None = None,
        exploration_c: float = 1.0,
        now: datetime | None = None,
    ) -> tuple[float, int, str]:
        """Prior UCB para (técnica, clase) con back-off jerárquico.

        Devuelve (prior, n_efectivo, etiqueta). Si la celda fina tiene menos de
        BACKOFF_MIN_OBS observaciones, hace back-off al nivel agregado (familia).
        Con cero datos el prior es 0.0 (comportamiento congelado, §6 reversible).
        """
        now = now or _now()
        records = self._read_valid()
        wsum, n_eff = self._cell_stats(
            records, profile=profile, family=family, technique_id=technique_id,
            channel=channel, canon_version=canon_version, now=now,
        )
        used_backoff = False
        if n_eff < BACKOFF_MIN_OBS:
            wsum_agg, n_agg = self._cell_stats(
                records, profile=profile, family=family,
                technique_id=_AGGREGATE_KEY, channel=channel,
                canon_version=canon_version, now=now,
            )
            if n_agg > 0:
                wsum, n_eff = wsum_agg, n_agg
                used_backoff = True
        if n_eff == 0:
            return 0.0, 0, "sin_datos"
        mean = wsum / n_eff
        # UCB1 sobre la media ponderada; la incertidumbre baja con n_efectivo.
        total = sum(
            1 for r in records
            if r["profile"] == profile and r["channel"] == channel
            and (canon_version is None or r.get("canon_version") == canon_version)
        )
        bonus = exploration_c * math.sqrt(math.log(max(total, 2)) / n_eff)
        prior = mean + bonus
        # P2: un resultado NEGATIVO debe poder REDUCIR la preferencia, no solo
        # subirla. Con media < 0.5 (la observada es peor que indeterminada), el
        # bonus de exploración se ATENÚA por la evidencia negativa acumulada:
        # explorar fracasos es razonable; tratarlos como incertidumbre favorable
        # no. Con mean >= 0.5 el bonus UCB se conserva íntegro. El factor nunca
        # baja de 0: un historial de fallos acerca el prior a la media observada.
        if mean < 0.5:
            confidence = min(1.0, n_eff / BACKOFF_MIN_OBS)
            bonus *= (2.0 * mean) * confidence
            prior = mean + bonus
        label = f"ucb:{prior:.3f}(n={n_eff},backoff={used_backoff})"
        return prior, n_eff, label

    # -- agregación (back-off) --------------------------------------------
    def record_family_outcome(
        self,
        *,
        profile: str,
        family: str,
        channel: str,
        outcome: str,
        canon_version: str,
        value: float | None = None,
        run_id: str = "",
        recorded_at: datetime | None = None,
    ) -> dict[str, Any]:
        """Registra el outcome a nivel agregado (familia) para el back-off."""
        return self.record(
            profile=profile, family=family, technique_id=_AGGREGATE_KEY,
            channel=channel, outcome=outcome, canon_version=canon_version,
            value=value, run_id=run_id, recorded_at=recorded_at,
        )

    def summary(
        self,
        *,
        profile: str | None = None,
        canon_version: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lectura agregada de solo presentación (GUI): fila por celda.

        Celda = (profile, family, technique_id, channel, outcome); ``value``
        es la media de los valores numéricos si los hay. Orden determinista.
        No alimenta aprendizaje — solo lo muestra.
        """
        cells: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
        for r in self._read_valid():
            if profile is not None and r["profile"] != profile:
                continue
            if canon_version is not None and r.get("canon_version") != canon_version:
                continue
            key = (r["profile"], r["family"], r["technique_id"],
                   r["channel"], r["outcome"])
            cell = cells.setdefault(key, {
                "profile": r["profile"], "family": r["family"],
                "technique_id": r["technique_id"], "channel": r["channel"],
                "outcome": r["outcome"], "n": 0, "value_sum": 0.0, "value_n": 0,
            })
            cell["n"] += 1
            v = r.get("value")
            if isinstance(v, (int, float)):
                cell["value_sum"] += float(v)
                cell["value_n"] += 1
        out: list[dict[str, Any]] = []
        for key in sorted(cells):
            cell = dict(cells[key])
            value_n = cell.pop("value_n")
            value_sum = cell.pop("value_sum")
            cell["value"] = round(value_sum / value_n, 6) if value_n else None
            out.append(cell)
        return out

    # -- auditoría / invariante (§15.2) ------------------------------------
    def state_hash(self) -> str:
        """SHA-256 del contenido del store: hace comprobable el invariante.

        Dos ejecuciones con mismo seed y mismo hash DEBEN producir el mismo
        output (testable en CI).
        """
        if not self.path.exists():
            return hashlib.sha256(b"").hexdigest()
        return hashlib.sha256(self.path.read_bytes()).hexdigest()


def default_store(path: Path | str | None = None) -> TechniqueOutcomeStore:
    """Store por defecto en LOCALAPPDATA (mismo patrón que dossiers/ledger)."""
    return TechniqueOutcomeStore(path)
