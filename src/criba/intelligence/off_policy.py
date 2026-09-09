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
    - alguna acción carece de propensión de logging válida (sin contrafactual);
    - la candidata asigna propensión 0 a una acción tomada (violación de solape);
    - el ESS efectivo es demasiado bajo para un IC útil (< MIN_ESS).
    """
    if not decisions:
        return OffPolicyEstimate(
            value=None, verdict="UNRESOLVED", n_decisions=0, ess=0.0,
            ci_low=None, ci_high=None,
            reason="log vacío: sin decisiones con propensión no hay contrafactual",
        )

    pool = sorted({d.technique_id for d in decisions})
    weights: list[float] = []
    rewards: list[float] = []
    for d in decisions:
        if not (0.0 < d.propensity <= 1.0):
            return OffPolicyEstimate(
                value=None, verdict="UNRESOLVED", n_decisions=len(decisions),
                ess=0.0, ci_low=None, ci_high=None,
                reason=f"decisión sin propensión de logging válida: {d.technique_id}",
            )
        pi_e = float(candidate(d.technique_id, d.family, pool))
        if pi_e <= 0.0:
            return OffPolicyEstimate(
                value=None, verdict="UNRESOLVED", n_decisions=len(decisions),
                ess=0.0, ci_low=None, ci_high=None,
                reason=(
                    f"violación de solape: la candidata da propensión 0 a "
                    f"{d.technique_id}, tomada por la política de logging"
                ),
            )
        weights.append(pi_e / d.propensity)
        rewards.append(d.reward)

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
    """Compara candidata vs política de logging (la que generó las decisiones).

    El valor de la política de logging se estima con candidata == política b
    (razón 1.0 → SNIPS = media simple de rewards). Si los IC se solapan, el
    veredicto es UNRESOLVED: no se afirma diferencia sin evidencia (honestidad).
    """
    est_candidate = evaluate_policy(
        decisions, candidate, n_bootstrap=n_bootstrap, seed=seed)
    # Política de logging: propensión candidata = pi_b → razón 1.0.
    est_logging = evaluate_policy(
        decisions, lambda t, f, pool: 1.0, n_bootstrap=n_bootstrap, seed=seed)
    verdict = "UNRESOLVED"
    if (est_candidate.verdict == "ESTIMATED" and est_logging.verdict == "ESTIMATED"
            and est_candidate.ci_low is not None and est_logging.ci_high is not None
            and est_logging.ci_low is not None and est_candidate.ci_high is not None):
        if est_candidate.ci_low > est_logging.ci_high:
            verdict = "CANDIDATE_BETTER"
        elif est_logging.ci_low > est_candidate.ci_high:
            verdict = "LOGGING_BETTER"
        else:
            verdict = "UNRESOLVED"  # IC solapados: no se afirma diferencia
    return {
        "verdict": verdict,
        "candidate": est_candidate.to_dict(),
        "logging": est_logging.to_dict(),
    }
