"""CRIBA Causal Engine — Composición de intervenciones.

Reemplaza el sistema anterior (overwrite de vectores) por:
- FamilySpec: firma causal declarativa
- Intervention: instancia concreta con operator + target + axis_delta
- compose(): semántica de interacción entre intervenciones
- accumulate_axes(): aplicación no-destructiva con tracking de interacciones
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence


# ═══════════════════════════════════════════════════════════════════════════════
# 1. EJES CAUSALES (AX01-AX16)
# ═══════════════════════════════════════════════════════════════════════════════

class Axis(str, Enum):
    """16 ejes causales canónicos del espacio de innovación."""
    AX01_OBJETIVO = "AX01"           # Qué resultado se maximiza/minimiza
    AX02_ACTOR = "AX02"              # Quién decide, ejecuta, valida
    AX03_INCENTIVO = "AX03"          # Por qué actúa un actor
    AX04_RECURSO = "AX04"            # Qué recursos existen/faltan
    AX05_INFORMACION = "AX05"        # Qué se sabe y cómo circula
    AX06_EVIDENCIA = "AX06"          # Confianza, prueba, incertidumbre
    AX07_CAUSALIDAD = "AX07"         # Qué provoca qué
    AX08_TIEMPO = "AX08"             # Cuándo y en qué orden
    AX09_ESTRUCTURA = "AX09"        # Cómo están conectados
    AX10_ESCALA = "AX10"            # Tamaño, resolución, nivel
    AX11_CONTROL = "AX11"           # Humano, regla, algoritmo
    AX12_RIESGO = "AX12"            # Fallos, redundancia, recuperación
    AX13_MERCADO = "AX13"           # Adopción, competencia, sustitución
    AX14_COMPORTAMIENTO = "AX14"    # Decisión, cognición, hábito
    AX15_FISICO = "AX15"            # Materia, energía, fabricación
    AX16_EXPLORACION = "AX16"       # Cómo se abandona lo conocido


# ═══════════════════════════════════════════════════════════════════════════════
# 2. TIPOS DE OPERADOR
# ═══════════════════════════════════════════════════════════════════════════════

class OperatorType(str, Enum):
    """Tipos de intervención causal.
    
    Clave: operadores distintos sobre el mismo eje producen estados 
    cualitativamente diferentes. INVERT(AX09) ≠ REMOVE(AX09).
    """
    # Estructurales
    INVERT = "INVERT"           # Invierte relación (A→B → B→A)
    REMOVE = "REMOVE"           # Elimina elemento central
    DISTRIBUTE = "DISTRIBUTE"   # Distribuye en nodos
    CENTRALIZE = "CENTRALIZE"   # Concentra en hub
    MODULARIZE = "MODULARIZE"   # Descompone en módulos
    REPLICATE = "REPLICATE"     # Duplica para redundancia
    
    # Objetivo/Incentivo
    ADD = "ADD"                 # Añade objetivo/condición
    REMOVE_OBJ = "REMOVE_OBJ"   # Elimina objetivo
    SWAP = "SWAP"               # Intercambia primario/secundario
    EXTREMIZE = "EXTREMIZE"     # Lleva al extremo
    TRADEOFF = "TRADEOFF"       # Hace explícito tradeoff
    
    # Informacionales
    REVEAL = "REVEAL"           # Hace visible lo oculto
    HIDE = "HIDE"               # Oculta información
    AGGREGATE = "AGGREGATE"     # Combina fuentes
    DISAGGREGATE = "DISAGGREGATE"  # Separa granularidad
    
    # Temporales
    ACCELERATE = "ACCELERATE"   # Comprime tiempo
    DECELERATE = "DECELERATE"   # Expande tiempo
    RESEQUENCE = "RESEQUENCE"   # Cambia orden
    PARALLELIZE = "PARALLELIZE" # Secuencia → paralelo
    
    # Exploración
    ANALOGY = "ANALOGY"         # Mapea desde otro dominio
    RANDOMIZE = "RANDOMIZE"     # Variación estocástica
    COMBINE = "COMBINE"         # Cruza dominios
    EXAPT = "EXAPT"             # Recontextualiza uso
    
    # Control
    AUTOMATE = "AUTOMATE"       # Regla → algoritmo
    HUMANIZE = "HUMANIZE"      # Algoritmo → humano
    GATE = "GATE"               # Añade punto de decisión


# ═══════════════════════════════════════════════════════════════════════════════
# 3. ESTADO CAUSAL BASE
# ═══════════════════════════════════════════════════════════════════════════════

# Estado canónico de "lo conocido" — punto de partida de toda intervención
BASE_STATE: dict[Axis, float] = {
    Axis.AX01_OBJETIVO: 0.5,
    Axis.AX02_ACTOR: 0.5,
    Axis.AX03_INCENTIVO: 0.5,
    Axis.AX04_RECURSO: 0.5,
    Axis.AX05_INFORMACION: 0.5,
    Axis.AX06_EVIDENCIA: 0.5,
    Axis.AX07_CAUSALIDAD: 0.5,
    Axis.AX08_TIEMPO: 0.5,
    Axis.AX09_ESTRUCTURA: 0.5,
    Axis.AX10_ESCALA: 0.5,
    Axis.AX11_CONTROL: 0.5,
    Axis.AX12_RIESGO: 0.5,
    Axis.AX13_MERCADO: 0.5,
    Axis.AX14_COMPORTAMIENTO: 0.5,
    Axis.AX15_FISICO: 0.5,
    Axis.AX16_EXPLORACION: 0.5,
}


# ═══════════════════════════════════════════════════════════════════════════════
# 4. ESPECIFICACIÓN DE FAMILIA
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class FamilySpec:
    """Firma causal declarativa de una familia de innovación.
    
    Una familia no es una categoría temática — es un mecanismo causal
    con eje primario, ejes secundarios, y operador característico.
    """
    family_id: str
    name: str
    operator: OperatorType
    primary_axis: Axis
    secondary_axes: Mapping[Axis, float] = field(default_factory=dict)
    strength: float = 1.0
    targets: frozenset[str] = frozenset()
    preconditions: tuple[str, ...] = ()
    description: str = ""
    
    def __post_init__(self):
        # Validar que strength está en [0, 1]
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError(f"strength debe estar en [0,1], got {self.strength}")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. INTERVENCIÓN CONCRETA
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Intervention:
    """Instancia concreta de una intervención causal.
    
    Diferencia con FamilySpec:
    - FamilySpec: declarativo, reusable, abstracto
    - Intervention: concreto, anclado a un problema, con target específico
    """
    operator: OperatorType
    target: str                    # Elemento concreto del problema
    axis_delta: Mapping[Axis, float]  # Efecto causal
    family_id: str
    params: Mapping[str, Any] = field(default_factory=dict)
    strength: float = 1.0
    
    def axis_affected(self) -> set[Axis]:
        """Retorna el conjunto de ejes afectados (delta ≠ 0)."""
        return {axis for axis, delta in self.axis_delta.items() if abs(delta) > 0.01}


# ═══════════════════════════════════════════════════════════════════════════════
# 6. INTERACCIÓN ENTRE INTERVENCIONES
# ═══════════════════════════════════════════════════════════════════════════════

class InteractionType(str, Enum):
    """Tipo de interacción entre dos intervenciones."""
    ORTHOGONAL = "ORTHOGONAL"       # Ejes distintos, sin interacción
    REINFORCING = "REINFORCING"     # Mismo efecto, se refuerzan
    OVERLAPPING = "OVERLAPPING"     # Solapamiento parcial
    CONFLICTING = "CONFLICTING"     # Efectos opuestos, se cancelan parcialmente
    CANCELLING = "CANCELLING"       # Efectos exactamente opuestos
    DEPENDENT = "DEPENDENT"         # B requiere A para funcionar
    SYNERGISTIC = "SYNERGISTIC"     # El combinado > suma de partes


def compose(a: Intervention, b: Intervention) -> InteractionType:
    """Determina la interacción entre dos intervenciones.
    
    Clave para deduplicación y scoring:
    - INVERT(X) + INVERT(X) → CANCELLAR (vuelve al origen)
    - INVERT(X) + REMOVE(X) → CONFLICTING (direcciones opuestas)
    - DISTRIBUTE(X) + MODULARIZE(X) → SYNERGISTIC (se refuerzan)
    """
    axes_a = a.axis_affected()
    axes_b = b.axis_affected()
    
    # Sin solapamiento de ejes → ortogonal
    if not axes_a & axes_b:
        return InteractionType.ORTHOGONAL
    
    # Mismo operador + mismo target → potencial cancelación o refuerzo
    if a.operator == b.operator and a.target == b.target:
        if a.operator in (OperatorType.INVERT, OperatorType.SWAP):
            # INVERT dos veces = identidad
            return InteractionType.CANCELLING
        else:
            # Otros operadores se refuerzan
            return InteractionType.REINFORCING
    
    # Operadores opuestos sobre mismo eje
    opposites = {
        (OperatorType.INVERT, OperatorType.CENTRALIZE),
        (OperatorType.DISTRIBUTE, OperatorType.CENTRALIZE),
        (OperatorType.REMOVE, OperatorType.ADD),
        (OperatorType.REMOVE, OperatorType.DISTRIBUTE),
        (OperatorType.HIDE, OperatorType.REVEAL),
        (OperatorType.AUTOMATE, OperatorType.HUMANIZE),
        (OperatorType.ACCELERATE, OperatorType.DECELERATE),
    }
    if (a.operator, b.operator) in opposites or (b.operator, a.operator) in opposites:
        if axes_a & axes_b:
            return InteractionType.CONFLICTING
    
    # Operadores complementarios
    synergistic = {
        (OperatorType.DISTRIBUTE, OperatorType.MODULARIZE),
        (OperatorType.REVEAL, OperatorType.AUTOMATE),
        (OperatorType.ANALOGY, OperatorType.COMBINE),
        (OperatorType.RESEQUENCE, OperatorType.PARALLELIZE),
    }
    if (a.operator, b.operator) in synergistic or (b.operator, a.operator) in synergistic:
        return InteractionType.SYNERGISTIC
    
    # Solapamiento parcial por defecto
    return InteractionType.OVERLAPPING


# ═══════════════════════════════════════════════════════════════════════════════
# 7. ESTADO CAUSAL COMPUESTO
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CausalState:
    """Estado causal acumulado con tracking de intervenciones.
    
    Reemplaza al vector plano anterior. Ahora cada estado sabe CÓMO llegó
    (intervenciones aplicadas) y puede calcular interacciones.
    """
    vector: dict[Axis, float] = field(default_factory=lambda: dict(BASE_STATE))
    interventions: list[Intervention] = field(default_factory=list)
    interactions: list[tuple[int, int, InteractionType]] = field(default_factory=list)
    
    def apply(self, spec: FamilySpec, target: str, context: dict[str, Any] | None = None) -> Intervention:
        """Aplica una familia, produciendo una intervención acumulable.
        
        No sobrescribe el vector — acumula y compone.
        """
        # 1. Instanciar la intervención
        intervention = instantiate(spec, self, target, context)
        
        # 2. Acumular ejes (no destructivo)
        self.vector = accumulate_axes(self.vector, intervention.axis_delta)
        
        # 3. Registrar intervención
        self.interventions.append(intervention)
        
        # 4. Calcular interacciones con intervenciones previas
        for i, prev in enumerate(self.interventions[:-1]):
            interaction = compose(prev, intervention)
            self.interactions.append((i, len(self.interventions) - 1, interaction))
        
        return intervention
    
    def moved_axes(self) -> set[Axis]:
        """Ejes que se movieron desde el estado base."""
        return {axis for axis, val in self.vector.items() 
                if abs(val - BASE_STATE.get(axis, 0.5)) > 0.01}
    
    def is_cancelled(self) -> bool:
        """True si las intervenciones se cancelan mutuamente."""
        return any(it == InteractionType.CANCELLING for _, _, it in self.interactions)
    
    def redundancy_score(self) -> float:
        """Score de redundancia: 0 = complementarias, 1 = totalmente redundantes."""
        if not self.interactions:
            return 0.0
        weights = {
            InteractionType.ORTHOGONAL: 0.0,
            InteractionType.SYNERGISTIC: 0.1,
            InteractionType.DEPENDENT: 0.2,
            InteractionType.OVERLAPPING: 0.5,
            InteractionType.REINFORCING: 0.7,
            InteractionType.CONFLICTING: 0.8,
            InteractionType.CANCELLING: 1.0,
        }
        return sum(weights[it] for _, _, it in self.interactions) / len(self.interactions)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. FUNCIONES DE COMPOSICIÓN
# ═══════════════════════════════════════════════════════════════════════════════

def instantiate(
    spec: FamilySpec,
    state: CausalState,
    target: str,
    context: dict[str, Any] | None = None,
) -> Intervention:
    """Instancia una FamilySpec en una Intervention concreta.
    
    Deriva axis_delta del spec + estado actual + target.
    """
    context = context or {}
    
    # Calcular delta basado en operador y eje primario
    axis_delta: dict[Axis, float] = {}
    
    # Efecto primario
    primary = spec.primary_axis
    strength = spec.strength
    
    # El delta depende del operador
    if spec.operator == OperatorType.INVERT:
        axis_delta[primary] = -0.6 * strength  # Invierte dirección
    elif spec.operator == OperatorType.REMOVE:
        axis_delta[primary] = -0.8 * strength  # Elimina
    elif spec.operator == OperatorType.DISTRIBUTE:
        axis_delta[primary] = 0.5 * strength
    elif spec.operator == OperatorType.CENTRALIZE:
        axis_delta[primary] = -0.5 * strength
    elif spec.operator == OperatorType.MODULARIZE:
        axis_delta[primary] = 0.4 * strength
    elif spec.operator == OperatorType.REVEAL:
        axis_delta[primary] = 0.7 * strength
    elif spec.operator == OperatorType.HIDE:
        axis_delta[primary] = -0.7 * strength
    elif spec.operator == OperatorType.AUTOMATE:
        axis_delta[primary] = 0.6 * strength
    elif spec.operator == OperatorType.ANALOGY:
        axis_delta[primary] = 0.5 * strength
    elif spec.operator == OperatorType.EXTREMIZE:
        axis_delta[primary] = 0.9 * strength
    else:
        axis_delta[primary] = 0.3 * strength
    
    # Efectos secundarios
    for axis, weight in spec.secondary_axes.items():
        axis_delta[axis] = weight * strength * 0.5
    
    return Intervention(
        operator=spec.operator,
        target=target,
        axis_delta=axis_delta,
        family_id=spec.family_id,
        params=context,
        strength=strength,
    )


def accumulate_axes(
    current: dict[Axis, float],
    delta: Mapping[Axis, float],
) -> dict[Axis, float]:
    """Acumula deltas al vector actual con clamping [0, 1].
    
    No es overwrite: es acumulación con saturación.
    """
    result = dict(current)
    for axis, d in delta.items():
        result[axis] = max(0.0, min(1.0, result.get(axis, 0.5) + d))
    return result


def compose_interventions(state: CausalState) -> CausalState:
    """Recompone el estado considerando interacciones.
    
    Si dos intervenciones se cancelan, el estado refleja la cancelación.
    Si son sinérgicas, el efecto se amplifica.
    """
    # Ajustar por interacciones
    for i, j, interaction in state.interactions:
        a = state.interventions[i]
        b = state.interventions[j]
        
        if interaction == InteractionType.CANCELLING:
            # Cancelar: volver al estado base para esos ejes
            for axis in a.axis_affected() & b.axis_affected():
                state.vector[axis] = BASE_STATE.get(axis, 0.5)
        
        elif interaction == InteractionType.SYNERGISTIC:
            # Sinergia: amplificar efecto
            for axis in a.axis_affected() & b.axis_affected():
                current = state.vector.get(axis, 0.5)
                base = BASE_STATE.get(axis, 0.5)
                # Alejarse más del base
                direction = 1 if current > base else -1
                state.vector[axis] = max(0.0, min(1.0, current + direction * 0.1))
    
    return state


# ═══════════════════════════════════════════════════════════════════════════════
# 9. SELECTOR CON PENALIZACIÓN DE REDUNDANCIA
# ═══════════════════════════════════════════════════════════════════════════════

def select_families(
    problem_vector: dict[Axis, float],
    candidates: list[FamilySpec],
    n_select: int = 5,
) -> list[tuple[FamilySpec, float]]:
    """Selecciona familias maximizando cobertura causal y diversidad.
    
    score = fit + coverage_gain + operator_diversity + target_diversity
            - causal_overlap - semantic_redundancy
    """
    selected: list[tuple[FamilySpec, float]] = []
    covered_axes: set[Axis] = set()
    used_operators: set[OperatorType] = set()
    used_targets: set[str] = set()
    
    remaining = list(candidates)
    
    for _ in range(n_select):
        if not remaining:
            break
        
        scores: list[tuple[FamilySpec, float]] = []
        for spec in remaining:
            # Fit: qué tan bien encaja con el problema
            fit = _axis_match(problem_vector, spec)
            
            # Coverage gain: ejes nuevos que aporta
            new_axes = {spec.primary_axis} | set(spec.secondary_axes.keys())
            coverage_gain = len(new_axes - covered_axes) / max(1, len(new_axes))
            
            # Operator diversity: operador no usado
            operator_diversity = 0.3 if spec.operator not in used_operators else 0.0
            
            # Target diversity: targets no usados
            target_diversity = 0.2 if spec.targets and not (spec.targets & used_targets) else 0.0
            
            # Causal overlap: penalización por solapamiento
            causal_overlap = len(new_axes & covered_axes) / max(1, len(new_axes))
            
            # Semantic redundancia: R = axis + operator + target + outcome
            semantic_redundancy = 0.0
            for prev_spec, _ in selected:
                R = semantic_redundancy_fn(spec, prev_spec)
                semantic_redundancy = max(semantic_redundancy, R)
            
            score = (
                fit * 0.3
                + coverage_gain * 0.25
                + operator_diversity * 0.2
                + target_diversity * 0.1
                - causal_overlap * 0.3
                - semantic_redundancy * 0.4
            )
            scores.append((spec, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        best_spec, best_score = scores[0]
        
        selected.append((best_spec, best_score))
        covered_axes |= {best_spec.primary_axis} | set(best_spec.secondary_axes)
        used_operators.add(best_spec.operator)
        used_targets |= best_spec.targets
        remaining = [s for s, _ in scores[1:]]
    
    return selected


def _axis_match(problem: dict[Axis, float], spec: FamilySpec) -> float:
    """Similitud entre vector de problema y firma de familia."""
    dot = 0.0
    norm_p = 0.0
    norm_s = 0.0
    
    for axis in Axis:
        p = problem.get(axis, 0.5)
        s = 0.0
        if axis == spec.primary_axis:
            s = spec.strength
        elif axis in spec.secondary_axes:
            s = spec.secondary_axes[axis]
        
        dot += p * s
        norm_p += p * p
        norm_s += s * s
    
    if norm_p == 0 or norm_s == 0:
        return 0.0
    return dot / (math.sqrt(norm_p) * math.sqrt(norm_s))


# ═══════════════════════════════════════════════════════════════════════════════
# 10. REDUNDANCIA SEMÁNTICA (R = axis + operator + target + outcome)
# ═══════════════════════════════════════════════════════════════════════════════

def semantic_redundancy_fn(
    a: FamilySpec | Intervention, 
    b: FamilySpec | Intervention
) -> float:
    """Calcula redundancia semántica entre dos intervenciones/familias.
    
    R = axis_similarity + operator_similarity + target_similarity + outcome_similarity
    
    Acepta tanto FamilySpec (abstracto) como Intervention (concreto).
    Para Intervention, usa target concreto y axis_delta real.
    """
    # Axis similarity: solapamiento de ejes afectados
    axes_a = _get_axes(a)
    axes_b = _get_axes(b)
    
    if not axes_a and not axes_b:
        axis_sim = 0.0
    elif not axes_a or not axes_b:
        axis_sim = 0.0
    else:
        axis_sim = len(axes_a & axes_b) / max(len(axes_a), len(axes_b))
    
    # Operator similarity
    op_sim = 1.0 if a.operator == b.operator else 0.0
    
    # Target similarity
    target_sim = _get_target_similarity(a, b)
    
    # Outcome similarity
    outcome_sim = _outcome_similarity(_get_delta(a), _get_delta(b))
    
    R = (
        axis_sim * 0.2
        + op_sim * 0.35
        + target_sim * 0.30
        + outcome_sim * 0.15
    )
    
    return min(1.0, R)


def _get_axes(item: FamilySpec | Intervention) -> set[Axis]:
    """Obtiene el conjunto de ejes afectados."""
    if isinstance(item, Intervention):
        return item.axis_affected()
    return {item.primary_axis} | set(item.secondary_axes)


def _get_target_similarity(a: FamilySpec | Intervention, b: FamilySpec | Intervention) -> float:
    """Calcula similitud de targets."""
    # Para Intervention: comparar target concreto
    if isinstance(a, Intervention) and isinstance(b, Intervention):
        return 1.0 if a.target == b.target else 0.0
    
    # Para FamilySpec: comparar frozenset de targets
    if isinstance(a, FamilySpec) and isinstance(b, FamilySpec):
        if a.targets and b.targets:
            return len(a.targets & b.targets) / max(len(a.targets), len(b.targets))
        return 0.0
    
    # Mixto: comparar targets de FamilySpec con target de Intervention
    if isinstance(a, FamilySpec) and isinstance(b, Intervention):
        return 1.0 if b.target in a.targets else 0.0
    if isinstance(a, Intervention) and isinstance(b, FamilySpec):
        return 1.0 if a.target in b.targets else 0.0
    
    return 0.0


def _get_delta(item: FamilySpec | Intervention) -> dict[Axis, float]:
    """Obtiene el vector de deltas (outcome)."""
    if isinstance(item, Intervention):
        return dict(item.axis_delta)
    # Para FamilySpec, construir delta desde primary_axis + secondary_axes
    delta = {item.primary_axis: item.strength}
    delta.update(item.secondary_axes)
    return delta


def _outcome_similarity(
    delta_a: Mapping[Axis, float], 
    delta_b: Mapping[Axis, float]
) -> float:
    """Similitud entre dos vectores de delta (outcome).
    
    1.0 = mismo efecto, 0.0 = efectos completamente distintos.
    """
    all_axes = set(delta_a) | set(delta_b)
    if not all_axes:
        return 0.0
    
    # Distancia euclídea normalizada
    dist = math.sqrt(sum(
        (delta_a.get(axis, 0.0) - delta_b.get(axis, 0.0)) ** 2
        for axis in all_axes
    ))
    max_dist = math.sqrt(len(all_axes))  # máxima distancia posible
    return 1.0 - (dist / max_dist) if max_dist > 0 else 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# 11. EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "Axis",
    "OperatorType",
    "FamilySpec",
    "Intervention",
    "InteractionType",
    "CausalState",
    "BASE_STATE",
    "compose",
    "instantiate",
    "accumulate_axes",
    "compose_interventions",
    "select_families",
    "semantic_redundancy_fn",
    "_outcome_similarity",
    "_get_axes",
    "_get_target_similarity",
    "_get_delta",
]
