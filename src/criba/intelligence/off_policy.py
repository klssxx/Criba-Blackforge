"""Evaluación off-policy de políticas de selección (BLUEPRINT §12.4, G3).

Pregunta que responde: «con los outcomes YA registrados bajo la política de
logging, cómo HABRÍA rendido una política candidata distinta SIN re-ejecutar la
lotería?». Es la forma honesta de comparar p. ej. dos valores de ADAPTIVE_BOOST
antes de comprometer uno en producción.

Método (estándar, referencias: Precup/Sutton/Singh 2000; Swaminathan & Joachims
2015 — self-normalized importance sampling, SNIPS):

  w_i = pi_e(a_i | x_i) / pi_b(a_i | x_i)          (razón de importancia)
  V_SNIPS = sum(w_i * r_i) / sum(w_i)              (auto-normalizado, menos varianza)

Reglas de honestidad (mismo patrón que outcome_store / dossier):
- Append-only JSONL de decisiones CON propensión pi_b registrada en el momento
  del sorteo (sin ella no hay contrafactual válido).
- El estimador exige SOLAPE: pi_b(a_i) > 0 para toda acción que la candidata
  podría tomar. En CRIBA se cumple por construcción: todo método conserva peso
  base 1.0 (exploración nunca muere, §12.4), así que pi_b > 0 siempre.
- Si el log está vacío, sin propensiones, o el IC bootstrap indica evidencia
  insuficiente: veredicto UNRESOLVED honesto — NUNCA se afirma mejora sin
  evidencia.
- Determinista: mismo log + misma política candidata = mismo estimador. El
  bootstrap usa una semilla fija explícita (no el RNG global).
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

# Líneas malformadas del log se excluyen con RuntimeWarning (patrón dossier):
# el aprendizaje nunca se rompe por historial ambiguo.

DEFAULT_BOOTSTRAP_SAMPLES = 1000
BOOTSTRAP_SEED = 20260909  # fija y documentada: reproducibilidad del IC
MIN_ESS = 10.0  # tamaño efectivo mínimo para un IC bootstrap fiable


def _default_log_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    return base / "CRIBA-Blackforge" / "outcomes" / "policy_decisions.jsonl"


@dataclass(frozen=True)
class LoggedDecision:
    """Una decisión de selección con la propensión de la política de logging."""

    technique_id: str
    family: str
    propensity: float          # pi_b(a|x) registrada en el sorteo
    reward: float              # outcome observado posterior [0,1]
    profile: str = "CRIBA"
    channel: str = "verdict"
    run_id: str = ""
    recorded_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "technique_id": self.technique_id,
            "family": self.family,
            "propensity": self.propensity,
            "reward": self.reward,
            "profile": self.profile,
            "channel": self.channel,
            "run_id": self.run_id,
            "recorded_at": self.recorded_at,
        }


def append_decision(path: Path | str, decision: LoggedDecision) -> None:
    """Registra una decisión con propensión (append-only, auditable)."""
    if not 0.0 < decision.propensity <= 1.0:
        raise ValueError(f"propensión fuera de (0,1]: {decision.propensity}")
    if not 0.0 <= decision.reward <= 1.0:
        raise ValueError(f"reward fuera de [0,1]: {decision.reward}")
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    rec = decision.to_dict()
    if not rec["recorded_at"]:
        rec["recorded_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with p.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(rec, ensure_ascii=False) + "\n")


def read_decisions(path: Path | str) -> list[LoggedDecision]:
    """Lee y valida el log; las líneas malformadas se excluyen con warning."""
    p = Path(path)
    if not p.exists():
        return []
    out: list[LoggedDecision] = []
    malformed = 0
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if not isinstance(rec, dict):
            malformed += 1
            continue
        try:
            out.append(LoggedDecision(
                technique_id=str(rec["technique_id"]),
                family=str(rec["family"]),
                propensity=float(rec["propensity"]),
                reward=float(rec["reward"]),
                profile=str(rec.get("profile", "CRIBA")),
                channel=str(rec.get("channel", "verdict")),
                run_id=str(rec.get("run_id", "")),
                recorded_at=str(rec.get("recorded_at", "")),
            ))
        except (KeyError, TypeError, ValueError):
            malformed += 1
    if malformed:
        warnings.warn(
            f"off-policy: {malformed} líneas malformadas excluidas del log",
            RuntimeWarning, stacklevel=2,
        )
    return out


def log_hash(path: Path | str) -> str:
    """SHA-256 del log: hace comprobable el invariante de reproducibilidad."""
    p = Path(path)
    if not p.exists():
        return hashlib.sha256(b"").hexdigest()
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rehydrate_rewards(
    decisions: Sequence[LoggedDecision],
    outcome_store: Any,
    *,
    profile: str = "CRIBA",
    canon_version: str | None = None,
) -> list[LoggedDecision]:
    """Une la recompensa real a cada decisión desde el outcome_store.

    El sorteo registra la decisión con reward pendiente (0.0); la evaluación la
    rehidrata con el prior VERDICT/OBSERVED de su ``technique_id`` — el outcome
    real observado para ese método. Sin outcome conocido la recompensa queda 0.0
    (exploración sin señal: honesto, no se inventa resultado).

    Devuelve NUEVAS instancias (LoggedDecision es inmutable); las decisiones con
    reward ya >0 se respetan (un log curado manualmente no se sobrescribe).
    """
    from .outcome_store import CHANNEL_OBSERVED, CHANNEL_VERDICT

    out: list[LoggedDecision] = []
    for d in decisions:
        if d.reward > 0.0:
            out.append(d)
            continue
        # P2: OBSERVED (evidencia práctica) CAPA a VERDICT (teórica). Un fallo
        # real observado no queda neutralizado por señal de antecedentes.
        prior_v = prior_o = 0.0
        n_v = n_o = 0
        try:
            for ch in (CHANNEL_VERDICT, CHANNEL_OBSERVED):
                prior, n_eff, _ = outcome_store.prior(
                    profile=d.profile or profile,
                    family=d.family,
                    technique_id=d.technique_id,
                    channel=ch,
                    canon_version=canon_version,
                )
                if ch == CHANNEL_VERDICT:
                    prior_v, n_v = prior, n_eff
                else:
                    prior_o, n_o = prior, n_eff
        except Exception:  # noqa: BLE001 — sin store la recompensa queda 0.0
            n_o = n_v = 0
        if n_o > 0:
            best = prior_o
        elif n_v > 0:
            best = prior_v
        else:
            best = 0.0
        if best != d.reward:
            out.append(LoggedDecision(
                technique_id=d.technique_id, family=d.family,
                propensity=d.propensity, reward=min(1.0, best),
                profile=d.profile, channel=d.channel, run_id=d.run_id,
                recorded_at=d.recorded_at,
            ))
        else:
            out.append(d)
    return out


# Política candidata: (technique_id, family, pool_disponible) -> propensión [0,1].
# Debe devolver >0 para toda acción con pi_b>0 (solape). Se inyecta como callable
# para no acoplar el estimador a una forma concreta de política.
CandidatePolicy = Callable[[str, str, Sequence[str]], float]


@dataclass(frozen=True)
class OffPolicyEstimate:
    """Resultado auditable de la evaluación off-policy."""

    value: float | None                 # estimación SNIPS, None si UNRESOLVED
    verdict: str                        # ESTIMATED | UNRESOLVED
    n_decisions: int
    ess: float                          # tamaño efectivo de muestra (Kish)
    ci_low: float | None
    ci_high: float | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "verdict": self.verdict,
            "n_decisions": self.n_decisions,
            "ess": round(self.ess, 3),
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "reason": self.reason,
        }


def _snips(weights: Sequence[float], rewards: Sequence[float]) -> float:
    total_w = sum(weights)
    if total_w <= 0.0:
        return 0.0
    return sum(w * r for w, r in zip(weights, rewards)) / total_w


def _ess(weights: Sequence[float]) -> float:
    """Tamaño efectivo de muestra de Kish: (sum w)^2 / sum w^2."""
    sw = sum(weights)
    sw2 = sum(w * w for w in weights)
    if sw2 <= 0.0:
        return 0.0
    return (sw * sw) / sw2


def evaluate_policy(
    decisions: Sequence[LoggedDecision],
    candidate: CandidatePolicy,
    *,
    n_bootstrap: int = DEFAULT_BOOTSTRAP_SAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> OffPolicyEstimate:
    """Estima el valor de una política candidata sobre decisiones logueadas.

    Devuelve UNRESOLVED (nunca una mejora inventada) cuando:
    - no hay decisiones;
    - alguna recompensa cae fuera de [0,1] o una propensión fuera de (0,1];
    - la candidata da propensión >0 a una acción SIN soporte en el logging
      (violación de solape en la dirección relevante: lo que la candidata
      podría elegir debe ser alcanzable por la política histórica);
    - la candidata concentra todo el peso en acciones jamás tomadas (suma de
      pesos cero: evidencia insuficiente);
    - el ESS efectivo es demasiado bajo para un IC útil (< MIN_ESS).

    Una candidata DETERMINISTA (propensión 0 a acciones que sí tomó el logging)
    es VÁLIDA: esas observaciones reciben peso cero y no cuentan (Swaminathan &
    Joachims 2015). Lo que NO es válido es lo contrario: que la candidata pueda
    elegir lo que el logging nunca pudo producir.
    """
    if n_bootstrap < 1:
        raise ValueError(f"n_bootstrap debe ser >= 1, got {n_bootstrap}")
    if not decisions:
        return OffPolicyEstimate(
            value=None, verdict="UNRESOLVED", n_decisions=0, ess=0.0,
            ci_low=None, ci_high=None,
            reason="log vacío: sin decisiones con propensión no hay contrafactual",
        )

    pool = sorted({d.technique_id for d in decisions})
    # Soporte real de la política de logging: acciones que SÍ tomó al menos una
    # vez (pi_b > 0 sobre ellas por construcción del log).
    support = {d.technique_id for d in decisions if d.propensity > 0.0}
    weights: list[float] = []
    rewards: list[float] = []
    for d in decisions:
        # Validación en frontera de evaluación (no solo en escritura): recompensa
        # finita en [0,1] y propensión en (0,1]. Fuera de contrato -> UNRESOLVED.
        if not (0.0 < d.propensity <= 1.0) or not (0.0 <= d.reward <= 1.0):
            return OffPolicyEstimate(
                value=None, verdict="UNRESOLVED", n_decisions=len(decisions),
                ess=0.0, ci_low=None, ci_high=None,
                reason=(
                    f"fuera de contrato: propensity={d.propensity}, "
                    f"reward={d.reward} (esperado prop en (0,1], reward en [0,1])"
                ),
            )
        pi_e = float(candidate(d.technique_id, d.family, pool))
        if pi_e < 0.0:
            pi_e = 0.0
        weights.append(pi_e / d.propensity)
        rewards.append(d.reward)

    # Solape en la dirección relevante: toda acción con propensión POSITIVA en la
    # candidata debe tener soporte en el logging. Lo inverso NO se exige.
    for tid in pool:
        pi_e = float(candidate(tid, next(d.family for d in decisions if d.technique_id == tid), pool))
        if pi_e > 0.0 and tid not in support:
            return OffPolicyEstimate(
                value=None, verdict="UNRESOLVED", n_decisions=len(decisions),
                ess=0.0, ci_low=None, ci_high=None,
                reason=(
                    f"violación de solape: la candidata da propensión >0 a "
                    f"{tid}, que la política de logging nunca produjo"
                ),
            )

    total_w = sum(weights)
    if total_w <= 0.0:
        return OffPolicyEstimate(
            value=None, verdict="UNRESOLVED", n_decisions=len(decisions),
            ess=0.0, ci_low=None, ci_high=None,
            reason="suma de pesos cero: la candidata no cubre ninguna acción con evidencia",
        )

    ess = _ess(weights)
    value = _snips(weights, rewards)
    if ess < MIN_ESS:
        return OffPolicyEstimate(
            value=None, verdict="UNRESOLVED", n_decisions=len(decisions), ess=ess,
            ci_low=None, ci_high=None,
            reason=f"ESS efectivo demasiado bajo ({ess:.1f} < {MIN_ESS}): IC no fiable",
        )

    # IC bootstrap percentil 95% con semilla fija (reproducible).
    rng = random.Random(seed)
    n = len(weights)
    boots: list[float] = []
    for _ in range(n_bootstrap):
        idx = [rng.randrange(n) for _ in range(n)]
        bw = [weights[i] for i in idx]
        br = [rewards[i] for i in idx]
        boots.append(_snips(bw, br))
    boots.sort()
    lo = boots[max(0, int(0.025 * n_bootstrap))]
    hi = boots[min(n_bootstrap - 1, int(0.975 * n_bootstrap))]
    return OffPolicyEstimate(
        value=round(value, 6), verdict="ESTIMATED", n_decisions=n, ess=ess,
        ci_low=round(lo, 6), ci_high=round(hi, 6),
        reason="SNIPS + IC bootstrap 95% (solape garantizado por peso base 1.0)",
    )


def compare_policies(
    decisions: Sequence[LoggedDecision],
    candidate: CandidatePolicy,
    *,
    n_bootstrap: int = DEFAULT_BOOTSTRAP_SAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """Compara candidata vs política de logging con DIFERENCIA PAREADA.

    El valor de la política de logging NO se estima con otra razón de
    importancia: se calcula con pesos UNITARIOS sobre sus propias decisiones
    (la media observada, su estimador natural insesgado). Comparar ambas con
    razón 1/pi_b inflaría artificialmente a una frente a la otra — el defecto
    que declaraba CANDIDATE_BETTER de una política contra sí misma.

    La diferencia se evalúa PAREADA sobre los mismos remuestreos bootstrap:
    dif_i = (w_i - 1) * r_i por observación, con w_i = pi_e/pi_b. Si la
    candidata ES la política de logging, dif_i = 0 para toda i y el IC cubre 0
    — jamás se declara ganadora de sí misma (invariante de identidad).
    """
    est_candidate = evaluate_policy(
        decisions, candidate, n_bootstrap=n_bootstrap, seed=seed)
    # Política de logging: media observada con pesos unitarios (su estimador
    # natural insesgado sobre sus propias decisiones), con IC bootstrap.
    est_logging = OffPolicyEstimate(
        value=None, verdict="UNRESOLVED", n_decisions=0, ess=0.0,
        ci_low=None, ci_high=None, reason="sin decisiones",
    )
    if decisions:
        rewards_obs = [d.reward for d in decisions]
        mean_obs = sum(rewards_obs) / len(rewards_obs)
        # IC bootstrap de la media observada (pesos unitarios)
        rng = random.Random(seed)
        n = len(rewards_obs)
        boots: list[float] = []
        for _ in range(n_bootstrap):
            idx = [rng.randrange(n) for _ in range(n)]
            boots.append(sum(rewards_obs[i] for i in idx) / n)
        boots.sort()
        lo = boots[max(0, int(0.025 * n_bootstrap))]
        hi = boots[min(n_bootstrap - 1, int(0.975 * n_bootstrap))]
        est_logging = OffPolicyEstimate(
            value=round(mean_obs, 6), verdict="ESTIMATED", n_decisions=n,
            ess=float(n), ci_low=round(lo, 6), ci_high=round(hi, 6),
            reason="media observada (pesos unitarios) + IC bootstrap 95%",
        )

    verdict = "UNRESOLVED"
    paired_diff: dict[str, Any] = {}
    if est_candidate.verdict == "ESTIMATED" and est_logging.verdict == "ESTIMATED":
        # Diferencia pareada por observación: dif_i = (w_i - 1) * r_i.
        pool = sorted({d.technique_id for d in decisions})
        diffs: list[float] = []
        for d in decisions:
            pi_e = max(0.0, float(candidate(d.technique_id, d.family, pool)))
            w = pi_e / d.propensity
            diffs.append((w - 1.0) * d.reward)
        mean_diff = sum(diffs) / len(diffs) if diffs else 0.0
        rng = random.Random(seed)
        n = len(diffs)
        boot_d: list[float] = []
        for _ in range(n_bootstrap):
            idx = [rng.randrange(n) for _ in range(n)]
            boot_d.append(sum(diffs[i] for i in idx) / n)
        boot_d.sort()
        d_lo = boot_d[max(0, int(0.025 * n_bootstrap))]
        d_hi = boot_d[min(n_bootstrap - 1, int(0.975 * n_bootstrap))]
        paired_diff = {
            "mean_diff": round(mean_diff, 6),
            "ci_low": round(d_lo, 6),
            "ci_high": round(d_hi, 6),
        }
        if d_lo > 0.0:
            verdict = "CANDIDATE_BETTER"
        elif d_hi < 0.0:
            verdict = "LOGGING_BETTER"
        else:
            verdict = "UNRESOLVED"  # IC pareado cubre 0: no se afirma diferencia
    return {
        "verdict": verdict,
        "candidate": est_candidate.to_dict(),
        "logging": est_logging.to_dict(),
        "paired_diff": paired_diff,
    }
