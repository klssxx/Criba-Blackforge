"""Causal model — FamilySpec registry for all operator families."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ── 16 causal axes ─────────────────────────────────────────────────────────
AX01_OBJETIVO = "ax01_objetivo_valor"
AX02_ACTOR = "ax02_actor_autoridad"
AX03_INCENTIVO = "ax03_incentivo_economia"
AX04_RECURSO = "ax04_recurso_restriccion"
AX05_INFORMACION = "ax05_informacion_conocimiento"
AX06_EVIDENCIA = "ax06_evidencia_incertidumbre"
AX07_CAUSALIDAD = "ax07_causalidad_dependencia"
AX08_TIEMPO = "ax08_tiempo_secuencia"
AX09_ESTRUCTURA = "ax09_estructura_topologia"
AX10_ESCALA = "ax10_escala_granularidad"
AX11_CONTROL = "ax11_control_automatizacion"
AX12_RESILIENCIA = "ax12_riesgo_resiliencia"
AX13_MERCADO = "ax13_mercado_adopcion"
AX14_COMPORTAMIENTO = "ax14_comportamiento_humano"
AX15_MATERIA = "ax15_materia_entorno"
AX16_EXPLORACION = "ax16_exploracion_novedad"

AXES = (
    AX01_OBJETIVO, AX02_ACTOR, AX03_INCENTIVO, AX04_RECURSO,
    AX05_INFORMACION, AX06_EVIDENCIA, AX07_CAUSALIDAD, AX08_TIEMPO,
    AX09_ESTRUCTURA, AX10_ESCALA, AX11_CONTROL, AX12_RESILIENCIA,
    AX13_MERCADO, AX14_COMPORTAMIENTO, AX15_MATERIA, AX16_EXPLORACION,
)

_LEGACY_TO_NEW = {
    "quien_decide": AX02_ACTOR,
    "cuando": AX08_TIEMPO,
    "evidencia_requerida": AX06_EVIDENCIA,
    "si_falla": AX12_RESILIENCIA,
    "topologia": AX09_ESTRUCTURA,
    "fuente_poder": AX03_INCENTIVO,
    "mecanismo_control": AX11_CONTROL,
    "flujo_informacion": AX05_INFORMACION,
    "recurso_principal": AX04_RECURSO,
    "relacion_confianza": AX14_COMPORTAMIENTO,
    "escala_operacion": AX10_ESCALA,
    "velocidad_respuesta": AX08_TIEMPO,
    "nivel_abstraccion": AX04_RECURSO,
    "orientacion_temporal": AX16_EXPLORACION,
    "tipo_innovacion": AX16_EXPLORACION,
}


class Operator(Enum):
    INVERT = "INVERT"
    REMOVE = "REMOVE"
    ADD = "ADD"
    DISTRIBUTE = "DISTRIBUTE"
    CENTRALIZE = "CENTRALIZE"
    MODULARIZE = "MODULARIZE"
    REPLACE = "REPLACE"
    SUBSTITUTE = "SUBSTITUTE"
    SCALE_UP = "SCALE_UP"
    SCALE_DOWN = "SCALE_DOWN"
    ACCELERATE = "ACCELERATE"
    DECELERATE = "DECELERATE"
    EXPAND = "EXPAND"
    CONTRACT = "CONTRACT"
    COUPLE = "COUPLE"
    DECOUPLE = "DECOUPLE"
    REVERSE = "REVERSE"
    SHIFT = "SHIFT"
    RANDOMIZE = "RANDOMIZE"
    OPTIMIZE = "OPTIMIZE"
    FRACTURE = "FRACTURE"
    ABSTRACT = "ABSTRACT"
    MATERIALIZE = "MATERIALIZE"
    REWARD = "REWARD"
    PENALIZE = "PENALIZE"
    SIMULATE = "SIMULATE"
    STRESS_TEST = "STRESS_TEST"
    ISOLATE = "ISOLATE"
    COUNTERFACTUAL = "COUNTERFACTUAL"
    RETRODICT = "RETRODICT"
    VISUALIZE = "VISUALIZE"
    ITERATE = "ITERATE"
    FRUGAL = "FRUGAL"
    EXPLOIT = "EXPLOIT"
    ANALOGY = "ANALOGY"
    CONNECT = "CONNECT"


class Interaction(Enum):
    ORTHOGONAL = "orthogonal"
    REINFORCING = "reinforcing"
    OVERLAPPING = "overlapping"
    CONFLICTING = "conflicting"
    CANCELLING = "cancelling"
    DEPENDENT = "dependent"
    SYNERGISTIC = "synergistic"


@dataclass(frozen=True)
class Intervention:
    operator: Operator
    target: str
    primary_axis: str
    secondary_axes: dict[str, float] = field(default_factory=dict)
    family_id: str = ""
    strength: float = 1.0


@dataclass
class CausalState:
    vector: dict[str, float]
    interventions: list[Intervention] = field(default_factory=list)

    @classmethod
    def zero(cls) -> "CausalState":
        return cls(vector={ax: 0.0 for ax in AXES})

    def snapshot(self) -> dict[str, float]:
        return dict(self.vector)

    def axes_changed(self, baseline: dict[str, float] | None = None) -> list[str]:
        base = baseline if baseline else {ax: 0.0 for ax in AXES}
        return [ax for ax in AXES if abs(self.vector.get(ax, 0.0) - base.get(ax, 0.0)) > 0.01]


def compose(a: Intervention, b: Intervention) -> Interaction:
    if a.primary_axis == b.primary_axis:
        if a.operator == b.operator:
            if a.operator in (Operator.INVERT, Operator.REVERSE):
                if a.target == b.target:
                    return Interaction.CANCELLING
                return Interaction.REINFORCING
            return Interaction.REINFORCING
        pairs = {
            (Operator.ADD, Operator.REMOVE), (Operator.CENTRALIZE, Operator.DISTRIBUTE),
            (Operator.SCALE_UP, Operator.SCALE_DOWN), (Operator.ACCELERATE, Operator.DECELERATE),
            (Operator.EXPAND, Operator.CONTRACT), (Operator.COUPLE, Operator.DECOUPLE),
        }
        if (a.operator, b.operator) in pairs or (b.operator, a.operator) in pairs:
            return Interaction.CONFLICTING
        return Interaction.OVERLAPPING
    if a.operator == b.operator:
        return Interaction.SYNERGISTIC
    return Interaction.ORTHOGONAL


def accumulate(state: CausalState, intervention: Intervention) -> CausalState:
    nv = dict(state.vector)
    delta = intervention.strength
    sign = _sign(intervention.operator)
    old = nv.get(intervention.primary_axis, 0.0)
    nv[intervention.primary_axis] = old + sign * delta
    for ax, w in intervention.secondary_axes.items():
        if ax in nv:
            nv[ax] += sign * delta * w
    return CausalState(vector=nv, interventions=state.interventions + [intervention])


def _sign(op: Operator) -> float:
    pos = {Operator.ADD, Operator.SCALE_UP, Operator.ACCELERATE, Operator.EXPAND,
           Operator.DISTRIBUTE, Operator.MODULARIZE, Operator.CENTRALIZE, Operator.REVERSE}
    neg = {Operator.REMOVE, Operator.SCALE_DOWN, Operator.DECELERATE, Operator.CONTRACT,
           Operator.INVERT}
    return 1.0 if op in pos else (-1.0 if op in neg else 0.0)


def causal_overlap(a: CausalState, b: CausalState) -> float:
    dot = sum(a.vector[ax] * b.vector[ax] for ax in AXES)
    ma = sum(v ** 2 for v in a.vector.values()) ** 0.5
    mb = sum(v ** 2 for v in b.vector.values()) ** 0.5
    return dot / (ma * mb) if ma >= 0.001 and mb >= 0.001 else 0.0


_EXPLICIT: dict[str, tuple[Operator, str]] = {
    "inversion": (Operator.INVERT, "objective_direction"),
    "inversion_operacion": (Operator.INVERT, "actor_role"),
    "inversion_estructural": (Operator.INVERT, "structure"),
    "actores_roles": (Operator.SHIFT, "actor_role"),
    "arquitectura": (Operator.INVERT, "governance"),
    "gobernanza": (Operator.DISTRIBUTE, "control"),
    "segmentacion": (Operator.MODULARIZE, "actor_scope"),
    "facilitacion": (Operator.DISTRIBUTE, "decision_rights"),
    "comunidad_participacion": (Operator.DISTRIBUTE, "voice"),
    "escenarios": (Operator.SHIFT, "time_horizon"),
    "prototipado": (Operator.SHIFT, "readiness"),
    "accion_preventiva": (Operator.SHIFT, "trigger_timing"),
    "accion_previa": (Operator.SHIFT, "preparation"),
    "accion_parcial": (Operator.SCALE_DOWN, "effort"),
    "accion_periodica": (Operator.SHIFT, "cadence"),
    "continuidad": (Operator.SCALE_UP, "flow"),
    "eliminacion_regeneracion": (Operator.REMOVE, "obsolescence"),
    "decision_secuencial": (Operator.SHIFT, "decision_timing"),
    "planificacion_online": (Operator.SHIFT, "planning_mode"),
    "estrategia": (Operator.SHIFT, "time_horizon"),
    "diagnostico": (Operator.INVERT, "assumption"),
    "verificacion": (Operator.STRESS_TEST, "claim"),
    "analogias": (Operator.SHIFT, "domain_source"),
    "ciencia_realidad": (Operator.STRESS_TEST, "hypothesis"),
    "investigacion": (Operator.STRESS_TEST, "question"),
    "filosofia": (Operator.ABSTRACT, "concept"),
    "extraccion": (Operator.ISOLATE, "signal"),
    "cambio_color": (Operator.SUBSTITUTE, "signal_encoding"),
    "cambio_parametro": (Operator.SUBSTITUTE, "control_knob"),
    "transicion_fase": (Operator.SUBSTITUTE, "state"),
    "expansion_termica": (Operator.SUBSTITUTE, "physical_regime"),
    "oxidacion": (Operator.SUBSTITUTE, "chemical_regime"),
    "ambiente_inerte": (Operator.ISOLATE, "environment"),
    "busqueda_unimodal": (Operator.CONTRACT, "search_space"),
    "busqueda_directa": (Operator.CONTRACT, "gradient_usage"),
    "busqueda_estocastica": (Operator.RANDOMIZE, "exploration"),
    "razonamiento_probabilistico": (Operator.SUBSTITUTE, "uncertainty_model"),
    "inferencia_probabilistica": (Operator.ABSTRACT, "latent_cause"),
    "cadenas_markov_monte_carlo": (Operator.SIMULATE, "distribution"),
    "decision_incertidumbre": (Operator.SUBSTITUTE, "decision_rule"),
    "modelos_bayesianos": (Operator.SUBSTITUTE, "inference_engine"),
    "chequeo_modelos": (Operator.STRESS_TEST, "model"),
    "comparacion_modelos": (Operator.STRESS_TEST, "criteria"),
    "prediccion_bayesiana": (Operator.SUBSTITUTE, "predictive_target"),
    "priors_bayesianos": (Operator.SUBSTITUTE, "prior_knowledge"),
    "evaluacion_modelos": (Operator.STRESS_TEST, "metric"),
    "datos_faltantes": (Operator.SUBSTITUTE, "imputation"),
    "modelos_mezcla": (Operator.SUBSTITUTE, "latent_structure"),
    "veneno_beneficio": (Operator.INVERT, "threat_signal"),
    "homogeneidad": (Operator.SUBSTITUTE, "material"),
    "diseno_adversarial": (Operator.STRESS_TEST, "threat_model"),
    "decision_riesgo": (Operator.SUBSTITUTE, "risk_appetite"),
    "morfologia": (Operator.SUBSTITUTE, "form_factor"),
    "recombinacion": (Operator.SUBSTITUTE, "connection_pattern"),
    "asimetria": (Operator.SUBSTITUTE, "symmetry"),
    "calidad_local": (Operator.SUBSTITUTE, "local_property"),
    "esfericidad": (Operator.SUBSTITUTE, "form_factor"),
    "fluidos": (Operator.SUBSTITUTE, "material_phase"),
    "membranas": (Operator.SUBSTITUTE, "boundary_form"),
    "material_poroso": (Operator.SUBSTITUTE, "internal_structure"),
    "ruptura_marco": (Operator.FRACTURE, "paradigma"),
    "diseno": (Operator.SHIFT, "design_philosophy"),
    "creacion_diseno": (Operator.MATERIALIZE, "concept"),
    "innovacion_frugal": (Operator.FRUGAL, "resource_usage"),
    "biomimetica": (Operator.ANALOGY, "biological_model"),
    "sustraccion": (Operator.REMOVE, "dependency"),
    "combinacion": (Operator.COUPLE, "functions"),
    "universalidad": (Operator.SUBSTITUTE, "resource_type"),
    "anidamiento": (Operator.MODULARIZE, "hierarchy"),
    "autoservicio": (Operator.COUPLE, "roles"),
    "copia": (Operator.SUBSTITUTE, "fidelity"),
    "objeto_desechable": (Operator.SUBSTITUTE, "durability"),
    "sustitucion_sistema": (Operator.SUBSTITUTE, "sensing_modality"),
    "materiales_compuestos": (Operator.SUBSTITUTE, "composition"),
    "colchon_previo": (Operator.ISOLATE, "failure_impact"),
    "salto_espacio": (Operator.ABSTRACT, "problem_frame"),
    "general": (Operator.CONNECT, "domain_bridge"),
    "juegos_innovacion": (Operator.SIMULATE, "scenario"),
    "algoritmos_poblacionales": (Operator.SIMULATE, "population"),
    "optimizacion_restringida": (Operator.OPTIMIZE, "constraints"),
    "aprendizaje_refuerzo": (Operator.OPTIMIZE, "policy"),
    "descenso_primer_orden": (Operator.OPTIMIZE, "gradient"),
    "descenso_segundo_orden": (Operator.OPTIMIZE, "curvature"),
    "descenso_adaptativo": (Operator.OPTIMIZE, "learning_rate"),
    "sostenibilidad": (Operator.SUBSTITUTE, "cycle_model"),
    "retroalimentacion": (Operator.COUPLE, "feedback_loop"),
    "etica": (Operator.SUBSTITUTE, "value_constraint"),
    "intermediario": (Operator.DISTRIBUTE, "mediation"),
    "contrapeso": (Operator.INVERT, "force_balance"),
    "seguridad": (Operator.EXPLOIT, "threat_model"),
    "cambio_incentivos": (Operator.REWARD, "behavior"),
    "ia_automatizacion": (Operator.SUBSTITUTE, "automation_level"),
    "confianza_gobernanza": (Operator.SUBSTITUTE, "trust_model"),
    "proceso": (Operator.VISUALIZE, "flow_hidden"),
    "mejora": (Operator.ITERATE, "cycle_speed"),
    "lente_avanzado": (Operator.SHIFT, "temporal_lens"),
    "historia_culturas": (Operator.RETRODICT, "historical_pattern"),
    "psicologia": (Operator.SUBSTITUTE, "cognitive_model"),
    "exploracion_aleatoria": (Operator.RANDOMIZE, "exploration_space"),
    "metainnovacion": (Operator.ABSTRACT, "innovation_model"),
    "supuestos_axiomas": (Operator.INVERT, "axiom"),
    "exaptacion_usos": (Operator.SHIFT, "function_context"),
    "reconfiguracion_espacial": (Operator.SUBSTITUTE, "spatial_layout"),
    "lenguaje_representacion": (Operator.SUBSTITUTE, "representation_model"),
    "metamarcos": (Operator.ABSTRACT, "meta_framework"),
    "logica_paradoja": (Operator.INVERT, "logical_premise"),
    "teoria_juegos": (Operator.SIMULATE, "game_model"),
    "modelos_negocio": (Operator.SUBSTITUTE, "business_model"),
    "prospectiva_escenarios": (Operator.SIMULATE, "future_model"),
    "redes_plataformas": (Operator.SUBSTITUTE, "network_topology"),
    "descomposicion": (Operator.MODULARIZE, "component_structure"),
    "eliminacion_simplificacion": (Operator.REMOVE, "redundancy"),
    "materiales_fabricacion": (Operator.SUBSTITUTE, "material_process"),
    "modularidad_arquitectura": (Operator.MODULARIZE, "module_boundary"),
    "fracaso_resiliencia": (Operator.INVERT, "failure_model"),
    "analogias_intersectoriales": (Operator.SHIFT, "cross_domain_source"),
    "ciencia_ficcion": (Operator.SIMULATE, "narrative_model"),
    "ciberseguridad": (Operator.EXPLOIT, "attack_surface"),
}


def _infer(family: str) -> tuple[Operator, str]:
    if family in _EXPLICIT:
        return _EXPLICIT[family]
    f = family.lower()
    for pat, op_tgt in [
        ("remove", (Operator.REMOVE, "component")),
        ("eliminat", (Operator.REMOVE, "component")),
        ("add", (Operator.ADD, "component")),
        ("distrib", (Operator.DISTRIBUTE, "control")),
        ("centrali", (Operator.CENTRALIZE, "control")),
        ("modular", (Operator.MODULARIZE, "structure")),
        ("scale", (Operator.SCALE_UP, "scope")),
        ("escala", (Operator.SCALE_UP, "scope")),
        ("replace", (Operator.REPLACE, "mechanism")),
        ("substitut", (Operator.SUBSTITUTE, "parameter")),
        ("cambio", (Operator.SUBSTITUTE, "parameter")),
        ("aceler", (Operator.ACCELERATE, "tempo")),
        ("coupl", (Operator.COUPLE, "components")),
        ("expand", (Operator.EXPAND, "scope")),
        ("contract", (Operator.CONTRACT, "scope")),
        ("shift", (Operator.SHIFT, "position")),
        ("random", (Operator.RANDOMIZE, "parameter")),
        ("optimiz", (Operator.OPTIMIZE, "parameter")),
        ("mejora", (Operator.OPTIMIZE, "parameter")),
    ]:
        if pat in f:
            return op_tgt
    return Operator.OPTIMIZE, "parameter"


def _secondaries(primary: str) -> dict[str, float]:
    m = {
        AX02_ACTOR: {AX11_CONTROL: 0.4, AX03_INCENTIVO: 0.3},
        AX08_TIEMPO: {AX12_RESILIENCIA: 0.3},
        AX09_ESTRUCTURA: {AX10_ESCALA: 0.3},
        AX06_EVIDENCIA: {AX05_INFORMACION: 0.4},
        AX04_RECURSO: {AX15_MATERIA: 0.3},
        AX03_INCENTIVO: {AX13_MERCADO: 0.3},
        AX11_CONTROL: {AX02_ACTOR: 0.3},
        AX16_EXPLORACION: {AX01_OBJETIVO: 0.3},
        AX13_MERCADO: {AX03_INCENTIVO: 0.3},
        AX14_COMPORTAMIENTO: {AX05_INFORMACION: 0.3},
        AX12_RESILIENCIA: {AX07_CAUSALIDAD: 0.3},
        AX10_ESCALA: {AX09_ESTRUCTURA: 0.3},
    }
    sec = m.get(primary, {AX06_EVIDENCIA: 0.2})
    return {k: v for k, v in sec.items() if k != primary}


def _build() -> dict[str, dict[str, Any]]:
    from .engine import _OPERATOR_EFFECT
    specs: dict[str, dict[str, Any]] = {}
    for fam, (legacy, val, ext) in _OPERATOR_EFFECT.items():
        ax = _LEGACY_TO_NEW.get(legacy, AX06_EVIDENCIA)
        op, tgt = _infer(fam)
        specs[fam] = {
            "operator": op, "target": tgt, "primary_axis": ax,
            "legacy_axis": legacy, "secondary_axes": _secondaries(ax),
            "val": val, "ext": ext,
        }
    return specs


FAMILY_SPECS: dict[str, dict[str, Any]] = _build()


def get_family_spec(family: str) -> dict[str, Any]:
    if family in FAMILY_SPECS:
        return FAMILY_SPECS[family]
    return {"operator": Operator.OPTIMIZE, "target": "parameter", "primary_axis": AX06_EVIDENCIA,
            "legacy_axis": "evidencia_requerida", "secondary_axes": {AX05_INFORMACION: 0.3},
            "val": "relacion no predicha", "ext": "relacion no predicha"}


def apply_family(state: CausalState, family: str, extreme: bool = False) -> CausalState:
    spec = get_family_spec(family)
    interv = Intervention(
        operator=spec["operator"], target=spec["target"], primary_axis=spec["primary_axis"],
        secondary_axes=spec.get("secondary_axes", {}), family_id=family,
        strength=1.5 if extreme else 1.0,
    )
    return accumulate(state, interv)


def legacy_apply_family(base: dict[str, str], family: str, extreme: bool = False) -> dict[str, str]:
    result = dict(base)
    spec = get_family_spec(family)
    val = spec["ext"] if extreme else spec["val"]
    # Update ALL legacy axes that map to this family's primary axis
    # (e.g., ax16_exploracion_novedad has both orientacion_temporal and tipo_innovacion)
    for leg, new in _LEGACY_TO_NEW.items():
        if new == spec["primary_axis"] and leg in result:
            result[leg] = val
    return result
