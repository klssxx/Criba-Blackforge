"""CRIBA innovation engine — MVP orchestrator.

Single canonical packet: MANDATORY_MODEL_PACKET (schema 2.0.0) extended with an
``innovation`` block, additively. Legacy fields are preserved. ``packet["ideas"]``
is the SAME object as ``packet["innovation"]["ideas"]`` (one canonical collection).

Separation of concerns (condition 5):
- orchestration:  ``activate`` (this file)
- local generation: ``cartograph_and_break`` / ``diverge`` (injectable hooks)
- genome validation/normalization: ``criba.genome``
- similarity / duplicates: ``criba.similarity``

The two HY3 call points are isolated as injectable functions so a cloud adapter
can replace the local implementation later without touching the rest.
"""
from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from .catalog import find_current
from .interprete.juez import JuezInterprete
from .constants import (
    CURRENT_CATALOG_VERSION,
    FEATURES,
    MAX_QUERY_CHARS,
    SELECTOR_VERSION,
    VALID_DECISIONS,
    VALID_MODES,
    VALID_PIPELINE_ACTIONS,
)
from .genome import ONTOLOGY_VERSION, normalize_proposal
from .methods import select_methods
from .selector import select

SCHEMA = "mandatory_model_packet"
SCHEMA_VERSION = "2.0.0"

INSTRUCTION = """Antes de responder al usuario, aplica obligatoriamente el paquete CRIBA adjunto.

Corriente activada: {current}.

Tu tarea es INNOVAR: usa el paquete para generar ideas nuevas, divergentes y accionables. Separa: 1. ideas generadas, 2. combinaciones inesperadas, 3. experimentos rápidos, 4. riesgos y cómo acotarlos.

No reveles cadena de pensamiento privada. Expón corriente activada, ideas, propuestas, riesgos, incertidumbre y respuesta final. Cuando falte información, no inventes datos."""

# ---------------------------------------------------------------------------
# Injectable generation hooks (condition 4). Local deterministic implementations
# today; swap for an HY3 adapter later without rewriting the orchestrator.
# ---------------------------------------------------------------------------
CartographFn = Callable[[str, dict[str, Any], dict[str, Any]], dict[str, Any]]
DivergeFn = Callable[[dict[str, Any], dict[str, Any], dict[str, Any], list[Any], str], list[Any]]


def _novelty_verbs(query: str) -> bool:
    lowered = query.casefold()
    return any(v in lowered for v in ("nuev", "innov", "disrupt", "alternativa", "idea",
                                       "crea", "diseñ", "mejor", "propuest", "experimento",
                                       "raro", "diferente", "original", "reinvent", "romper"))


def cartograph_and_break(query: str, context: dict[str, Any], selection: dict[str, Any]) -> dict[str, Any]:
    """Phase 1+2 (Cartografiar + Romper). Query-driven.

    Returns {known_space, assumptions, saturated_mechanisms, ruptures, domain,
             actors, assets, constraints, threats, opportunities}.
    """
    q = query.casefold()

    # --- Domain detection ---
    domain = "general"
    if any(w in q for w in ("api", " software", "sistema", "codigo", "algoritmo", "red")):
        domain = "tecnologia"
    elif any(w in q for w in ("seguridad", "ataque", "vulnerabilidad", "amenaza", "proteger", "defensa")):
        domain = "seguridad"
    elif any(w in q for w in ("negocio", "mercado", "cliente", "empresa", "ventas", "churn")):
        domain = "negocio"
    elif any(w in q for w in ("ia", "inteligencia artificial", "machine learning", "modelo")):
        domain = "ia"
    elif any(w in q for w in ("gobernanza", "dao", "organizacion", "equipo", "coordinar")):
        domain = "gobernanza"
    elif any(w in q for w in ("etica", "sesgo", "justo", "equidad", "niños")):
        domain = "etica"
    elif any(w in q for w in ("salud", "medico", "hospital", "paciente")):
        domain = "salud"
    elif any(w in q for w in ("educacion", "aprendizaje", "estudiante", "escuela")):
        domain = "educacion"
    elif any(w in q for w in ("transporte", "movilidad", "vehiculo", "logistica")):
        domain = "transporte"
    elif any(w in q for w in ("energia", "consumo", "edificio", "sostenible")):
        domain = "energia"
    elif any(w in q for w in ("alimento", "supermercado", "desperdicio", "cadena")):
        domain = "alimentos"
    elif any(w in q for w in ("trabajo", "descanso", "turno", "jornada")):
        domain = "recursos_humanos"

    # --- Query-specific elements extraction ---
    # Extract key nouns/concepts from query
    query_tokens = [w for w in q.split() if len(w) > 3]
    key_concepts = [w for w in query_tokens if w not in (
        "como", "podemos", "para", "que", "sin", "una", "del", "las", "los",
        "por", "con", "este", "esta", "todo", "mas", "sobre", "entre", "hacia",
    )]

    # --- Actors detection ---
    actors = []
    if any(w in q for w in ("usuario", "cliente", "persona", "gente", "equipo")):
        actors.append("usuarios/destinatarios finales")
    if any(w in q for w in ("empresa", "organizacion", "equipo")):
        actors.append("organizacion/implementadores")
    if any(w in q for w in ("atacante", "adversario", "amenaza")):
        actors.append("adversario/amenaza externa")
    if any(w in q for w in ("regulador", "normativa", "ley")):
        actors.append("regulador/autoridad")
    if not actors:
        actors = ["stakeholders no identificados"]

    # --- Assets detection ---
    assets = []
    if any(w in q for w in ("api", "datos", "informacion", "sistema")):
        assets.append("datos/informacion del sistema")
    if any(w in q for w in ("recurso", "energia", "tiempo", "dinero")):
        assets.append("recursos economicos/temporales")
    if any(w in q for w in ("confianza", "reputacion", "imagen")):
        assets.append("confianza/reputacion")
    if not assets:
        assets = ["valor central del problema"]

    # --- Known space (query-specific) ---
    known = []
    # Generic patterns adapted to domain
    if domain == "seguridad":
        known.extend([
            f"La defensa típica contra '{key_concepts[0] if key_concepts else 'amenazas'}' usa reglas estáticas.",
            "Se asume que el atacante sigue patrones conocidos.",
            "Más capas de defensa siempre reducen el riesgo.",
            "El perimeter security es suficiente si está bien configurado.",
        ])
    elif domain == "negocio":
        known.extend([
            f"La solución dominante para '{key_concepts[0] if key_concepts else 'el problema'}' es incremental.",
            "Se asume que más features = más valor para el cliente.",
            "El modelo de negocio actual es el único viable.",
            "Los competidores siguen la misma estrategia porque funciona.",
        ])
    elif domain == "tecnologia":
        known.extend([
            f"La arquitectura actual de '{key_concepts[0] if key_concepts else 'el sistema'}' es la correcta.",
            "Se asume que más automatización siempre reduce el error.",
            "La escalabilidad se logra añadiendo más recursos.",
            "El diseño convencional centraliza el control.",
        ])
    elif domain == "ia":
        known.extend([
            f"El modelo actual de '{key_concepts[0] if key_concepts else 'IA'}' captura la realidad.",
            "Se asume que más datos = mejor rendimiento.",
            "La explicabilidad es compatible con la complejidad.",
            "El sesgo se corrige con más datos de entrenamiento.",
        ])
    elif domain == "gobernanza":
        known.extend([
            f"La gobernanza de '{key_concepts[0] if key_concepts else 'el sistema'}' requiere jerarquía.",
            "Se asume que la descentralización implica caos.",
            "Las decisiones requieren consenso previo.",
            "La autoridad debe ser permanente para ser efectiva.",
        ])
    elif domain == "educacion":
        known.extend([
            f"El aprendizaje de '{key_concepts[0] if key_concepts else 'contenidos'}' requiere instrucción directa.",
            "Se asume que todos aprenden de la misma manera.",
            "La evaluación debe ser uniforme y estandarizada.",
            "El ritmo lo marca el profesor, no el estudiante.",
        ])
    elif domain == "salud":
        known.extend([
            f"El tratamiento de '{key_concepts[0] if key_concepts else 'condiciones'}' sigue protocolos establecidos.",
            "Se asume que la adherencia depende de la voluntad del paciente.",
            "La tecnología sanitaria es conservadora por necesidad.",
            "Los datos sensibles requieren centralización para seguridad.",
        ])
    elif domain == "transporte":
        known.extend([
            f"El transporte de '{key_concepts[0] if key_concepts else 'personas/materiales'}' depende de infraestructura fija.",
            "Se asume que más carreteras = menos congestión.",
            "Los vehículos privados son la forma dominante de moverse.",
            "La logística optimiza rutas, no el modelo completo.",
        ])
    elif domain == "energia":
        known.extend([
            f"El consumo de '{key_concepts[0] if key_concepts else 'energia'}' en edificios es inevitable.",
            "Se asume que la eficiencia requiere inversión alta.",
            "Los sistemas antiguos no pueden actualizarse sin reconstruir.",
            "El ahorro individual no impacta el consumo global.",
        ])
    elif domain == "alimentos":
        known.extend([
            f"El desperdicio de '{key_concepts[0] if key_concepts else 'alimentos'}' es un costo aceptable.",
            "Se asume que la cadena de suministro es óptima.",
            "Los consumidores compran lo que necesitan.",
            "La caducidad es una medida confiable de calidad.",
        ])
    elif domain == "recursos_humanos":
        known.extend([
            f"El descanso de '{key_concepts[0] if key_concepts else 'trabajadores'}' depende de la voluntad individual.",
            "Se asume que turnos largos = más productividad.",
            "El ritmo circadiano se adapta con el tiempo.",
            "La fatiga se gestiona con pausas ocasionales.",
        ])
    else:
        known.extend([
            f"El enfoque estándar para '{key_concepts[0] if key_concepts else 'este problema'}' es el único viable.",
            "Se asume que la solución conocida es la mejor.",
            "Más control siempre implica más seguridad.",
            "El coste de error es aceptable mientras sea raro.",
        ])

    # Add query-specific known space
    if "central" in q or "jerarqui" in q:
        known.append("La centralización permite control y trazabilidad.")
    if "automatic" in q or "automatiz" in q:
        known.append("La automatización elimina el error humano.")
    if "rapido" in q or "veloc" in q:
        known.append("La velocidad requiere simplificación de procesos.")

    # --- Assumptions (query-specific) ---
    assumptions = []
    for concept in key_concepts[:4]:
        assumptions.append(f"'{concept}' es la única manera de abordar el problema.")
    assumptions.extend([
        "Quien diseña conoce todos los casos límite.",
        "Más control siempre implica más seguridad.",
        "El coste de error es aceptable mientras sea raro.",
    ])
    assumptions = assumptions[:6]  # Max 6

    # --- Saturated mechanisms (domain-specific) ---
    saturated = []
    if domain == "seguridad":
        saturated = [
            {"mechanism": "firewall_rules", "reason": "reglas estáticas que el atacante aprende a evadir"},
            {"mechanism": "encryption", "reason": "cifrado que protege datos pero no decisiones"},
            {"mechanism": "access_control", "reason": "permisos que asumen identidad confiable"},
        ]
    elif domain == "negocio":
        saturated = [
            {"mechanism": "feature_addition", "reason": "añadir features sin validar valor real"},
            {"mechanism": "price_competition", "reason": "competir por precio destruye márgenes"},
            {"mechanism": "customer_surveys", "reason": "encuestas que predicen comportamiento pasado"},
        ]
    elif domain == "tecnologia":
        saturated = [
            {"mechanism": "horizontal_scaling", "reason": "añadir servidores sin optimizar código"},
            {"mechanism": "microservices", "reason": "dividir en servicios que crean complejidad"},
            {"mechanism": "caching", "reason": "caché que oculta problemas de diseño"},
        ]
    else:
        saturated = [
            {"mechanism": "verification", "reason": "ya se aplica en todas las capas."},
            {"mechanism": "automation", "reason": "empujada al límite sin margen de reversión."},
            {"mechanism": "consensus", "reason": "se invoca para todo, diluyendo responsabilidad."},
        ]

    # --- Ruptures (query-anchored) ---
    ruptures = []
    for i, a in enumerate(assumptions[:4], start=1):
        # Invert
        ruptures.append({
            "assumption_id": f"A{i:02d}",
            "operation": "invert",
            "result": f"En lugar de asumir '{a}', exigir lo contrario y diseñar para él.",
            "method_id": "M200-01",
            "query_anchor": key_concepts[0] if key_concepts else "problema",
            "domain": domain,
        })
        # Eliminate
        ruptures.append({
            "assumption_id": f"A{i:02d}",
            "operation": "eliminate",
            "result": f"Quitar el componente implícito en '{a}' y ver si el sistema sigue funcionando.",
            "method_id": "M100-01",
            "query_anchor": key_concepts[0] if key_concepts else "problema",
            "domain": domain,
        })
        # Substitute (new)
        ruptures.append({
            "assumption_id": f"A{i:02d}",
            "operation": "substitute",
            "result": f"Sustituir el mecanismo implícito en '{a}' por uno de otro dominio.",
            "method_id": "M800-01",
            "query_anchor": key_concepts[0] if key_concepts else "problema",
            "domain": domain,
        })

    # --- Opportunities (query-specific) ---
    opportunities = []
    if domain == "seguridad":
        opportunities = [
            "Usar la amenaza como motor de diseño (antifragilidad)",
            "Invertir la responsabilidad: que el sistema pruebe su propia seguridad",
            "Diseñar para el fallo, no para la perfección",
        ]
    elif domain == "negocio":
        opportunities = [
            "Crear mercados donde no existen competidores",
            "Convertir costos en fuentes de ingreso",
            "Diseñar experiencias que el cliente no esperaba",
        ]
    elif domain == "tecnologia":
        opportunities = [
            "Usar constrains como motor de innovación",
            "Invertir la arquitectura: datos que deciden, código que obedece",
            "Diseñar para la destrucción creativa del propio sistema",
        ]
    else:
        opportunities = [
            "Invertir la premisa central del problema",
            "Usar restricciones como ventaja competitiva",
            "Diseñar para el escenario que nadie considera",
        ]

    # --- Constraints ---
    constraints = []
    if "rapido" in q or "tiempo" in q:
        constraints.append("velocidad: la solución debe ser rápida de implementar")
    if "barato" in q or "coste" in q or "economic" in q:
        constraints.append("coste: la solución debe ser económica")
    if "seguro" in q or "proteger" in q:
        constraints.append("seguridad: la solución no debe crear nuevas vulnerabilidades")
    if "simple" in q or "facil" in q:
        constraints.append("simplicidad: la solución debe ser comprensible")
    if not constraints:
        constraints.append("viabilidad: la solución debe ser implementable")

    return {
        "known_space": known[:12],
        "assumptions": assumptions,
        "saturated_mechanisms": saturated,
        "ruptures": ruptures,
        "domain": domain,
        "actors": actors,
        "assets": assets,
        "constraints": constraints,
        "opportunities": opportunities,
        "key_concepts": key_concepts[:5],
        "counterexample": f"Contraejemplo: una situación donde '{key_concepts[0] if key_concepts else 'el enfoque actual'}' falla estrepitosamente.",
        "wants_novelty": _novelty_verbs(query),
    }


# ===========================================================================
# Two-layer ideation model (correct category separation):
#  - OPERATORS (39 families) = generation layer. They perturb the base idea.
#  - CAUSAL VARIABLES (15 axes) = verification layer (Zwicky-box parameters).
#    They are the ONLY criterion that measures whether divergence was real.
#  - CCA = cross-consistency assessment: an operator that moved no causal axis
#    produced cosmetic wording, not a new idea -> flagged divergence_real=False.
# ===========================================================================

# The 15 causal axes (expanded Zwicky box). 3x más espacio que antes.
_CAUSAL_AXES = (
    # Original 5
    "quien_decide", "cuando", "evidencia_requerida", "si_falla", "topologia",
    # New 10
    "fuente_poder", "mecanismo_control", "flujo_informacion", "recurso_principal",
    "relacion_confianza", "escala_operacion", "velocidad_respuesta",
    "nivel_abstraccion", "orientacion_temporal", "tipo_innovacion",
)

# Base causal configuration of the problem (from cartograph). Operators mutate it.
_BASE_CAUSAL = {
    "quien_decide": "operador humano",
    "cuando": "despues de validar",
    "evidencia_requerida": "reglas estaticas",
    "si_falla": "incidente detectado tarde",
    "topologia": "centralizada",
    "fuente_poder": "jerarquia formal",
    "mecanismo_control": "reglas escritas",
    "flujo_informacion": "lineal_arriba_abajo",
    "recurso_principal": "datos_y_codigo",
    "relacion_confianza": "confianza_ciega",
    "escala_operacion": "una_organizacion",
    "velocidad_respuesta": "lenta_reactiva",
    "nivel_abstraccion": "implementacion_detallada",
    "orientacion_temporal": "corto_plazo",
    "tipo_innovacion": "incremental",
}

# Each family declares (axis, normal_value, extreme_value). The extreme is
# FAMILY-SPECIFIC so two families over the same axis still produce distinct
# causal vectors -> real divergence, never cosmetic.
# 39 families mapped to 15 axes with distinct values.
_OPERATOR_EFFECT = {
    # --- Diagnóstico (evidencia) ---
    "diagnostico":            ("evidencia_requerida", "supuesto hecho explicito", "se asume lo contrario del supuesto y se prueba"),
    # --- Inversión (quien_decide) ---
    "inversion":              ("quien_decide", "el objetivo opuesto", "quien decide es el que antes no podia"),
    # --- Sustracción (si_falla) ---
    "sustraccion":            ("si_falla", "colapsa funcion oculta al quitar dependencia", "el fallo se vuelve visible y obligatorio"),
    # --- Restricciones (cuando) ---
    "restricciones":          ("cuando", "durante la ideacion con regla absurda", "nunca: se prohibe la opcion obvia"),
    # --- Actores/roles (quien_decide) ---
    "actores_roles":          ("quien_decide", "un actor distinto con la ultima palabra", "un actor externo sin historial decide"),
    # --- Incentivos (evidencia) ---
    "incentivos":             ("evidencia_requerida", "comportamiento recompensado", "se premia el error para revelar limites"),
    # --- Morfología (topología) ---
    "morfologia":             ("topologia", "reensamblada por dimensiones", "topologia efimera que se recrea por operacion"),
    # --- Recombinación (topología) ---
    "recombinacion":          ("topologia", "dos mecanismos cruzados en malla", "tres mecanismos en anillo cerrado"),
    # --- Analogías (evidencia) ---
    "analogias":              ("evidencia_requerida", "mapeo causal de otro dominio", "analogia de un dominio opuesto y no relacionado"),
    # --- Arquitectura (quien_decide) ---
    "arquitectura":           ("quien_decide", "una parte disidente del todo", "cada parte tiene veto y desacuerdo audible"),
    # --- Gobernanza (control) ---
    "gobernanza":             ("mecanismo_control", "trazabilidad de cada cambio", "cada cambio es reversible y auditable por terceros"),
    # --- Diseño adversarial (si_falla) ---
    "diseno_adversarial":     ("si_falla", "flanco explotado por atacante simulado", "el atacante participa en disenar la defensa"),
    # --- Escenarios (cuando) ---
    "escenarios":             ("cuando", "en el caso limite llevado al extremo", "en el peor caso ya ocurrido y reversible"),
    # --- Prototipado (cuando) ---
    "prototipado":            ("cuando", "antes de comprometer, en sombra", "en produccion con red de seguridad minima"),
    # --- Verificación (evidencia) ---
    "verificacion":           ("evidencia_requerida", "relacion reproducible no predicha", "la relacion se busca donde intuicion dice imposible"),
    # --- Decisión/riesgo (si_falla) ---
    "decision_riesgo":        ("si_falla", "dano contenido, no catastrofico", "el dano es el dato de entrenamiento"),
    # --- Nuevas familias expandidas ---
    "ruptura_marco":          ("tipo_innovacion", "rompe paradigma existente", "invierte la regla fundamental del dominio"),
    "salto_espacio":          ("nivel_abstraccion", "salta a meta-nivel", "resuelve desde un plano completamente distinto"),
    "general":                ("flujo_informacion", "conexion no obvia", "cruza dominios que parecian separados"),
    "lente_avanzado":         ("orientacion_temporal", "perspectiva temporal distinta", "mira el problema desde el futuro o el pasado"),
    "perspectiva":            ("relacion_confianza", "cuestiona la fuente", "asume que la premisa inicial es falsa"),
    "diseno_investigacion":   ("recurso_principal", "datos empiricos del usuario", "reemplaza supuestos con observacion directa"),
    "seguridad":              ("fuente_poder", "amenaza como motor", "usa la existencia de amenazas para diseñar soluciones"),
    "estrategia":             ("escala_operacion", "piensa en sistémico", "escala la solucion a nivel ecosistema"),
    "innovacion":             ("velocidad_respuesta", "experimento rapido", "valida en horas, no en meses"),
    "etica":                  ("mecanismo_control", "valor como restriccion", "el valor ético es una variable de diseño, no un postum"),
    "facilitacion":           ("flujo_informacion", "participacion masiva", "todos deciden, no solo expertos"),
    "ciencia_realidad":       ("evidencia_requerida", "method empirico", "exige reproduccion y falsabilidad"),
    "filosofia":              ("nivel_abstraccion", "primeros principios", "descompone hasta verdades atomicas"),
    "psicologia":             ("relacion_confianza", "inconsciente como variable", "factores emocionales y cognitivos explicitados"),
    "creacion_diseno":        ("recurso_principal", "materialidad como prototipo", "hace tangible lo abstracto"),
    "historia_culturas":      ("orientacion_temporal", "lecciones historicas", "busca patrones en civilizaciones pasadas"),
    "investigacion":          ("evidencia_requerida", "metodo cientifico", "hipotesis -> experimento -> conclusion"),
    "juegos_innovacion":      ("escala_operacion", "juego como laboratorio", "simula en miniature antes de escalar"),
    "diseno":                 ("tipo_innovacion", "diseno centrado en humano", "la experiencia del usuario define la solucion"),
    "mejora":                 ("velocidad_respuesta", "ciclo continuo", "medir -> ajustar -> medir sin parar"),
    "proceso":                ("flujo_informacion", "flujo visualizado", "hace visible lo que era invisible"),
    "negocio":                ("fuente_poder", "valor economico como palanca", "usa incentivos economicos para cambiar comportamiento"),
    "sostenibilidad":         ("escala_operacion", "ciclo cerrado", "diseña para que el residuo sea recurso"),
}

_VALID_MECH = {"elimination", "inversion", "isolation", "verification", "delegation", "prediction",
               "coordination", "consensus", "redundancy", "adaptation", "automation", "transformation",
               "market_exchange", "capability_proof"}


def _apply_family(family: str, base: dict[str, str], extreme: bool) -> dict[str, str]:
    """Apply ONE operator family to a causal-vector base (the REAL mutation used
    by diverge). Returns a new vector. Used directly by tests so they exercise the
    actual generator, not a replica."""
    ax, val, ext = _OPERATOR_EFFECT.get(family, ("evidencia_requerida", "relacion no predicha", "relacion no predicha"))
    cv = dict(base)
    cv[ax] = ext if extreme else val
    return cv


def _build_dynamic_base(query: str) -> dict[str, str]:
    """Build a query-adaptive base causal vector. Analyzes the query to set
    initial conditions that reflect the problem domain."""
    base = dict(_BASE_CAUSAL)
    q = query.casefold()

    # Domain-specific adaptations
    if any(w in q for w in ("api", "software", "sistema", "codigo", "algoritmo")):
        base["recurso_principal"] = "codigo_y_arquitectura"
        base["nivel_abstraccion"] = "nivel_sistemas"
    if any(w in q for w in ("seguridad", "ataque", "vulnerabilidad", "amenaza")):
        base["fuente_poder"] = "amenaza_como_motor"
        base["relacion_confianza"] = "desconfianza_verificable"
    if any(w in q for w in ("negocio", "mercado", "cliente", "empresa")):
        base["fuente_poder"] = "valor_economico"
        base["escala_operacion"] = "ecosistema_mercado"
    if any(w in q for w in ("ia", "inteligencia artificial", "machine learning", "algoritmo")):
        base["recurso_principal"] = "datos_y_modelos"
        base["nivel_abstraccion"] = "nivel_algoritmico"
    if any(w in q for w in ("gobernanza", "dao", "organizacion", "equipo")):
        base["mecanismo_control"] = "acuerdos_emergentes"
        base["flujo_informacion"] = "distribuido"
    if any(w in q for w in ("etica", "sesgo", "justo", "equidad")):
        base["mecanismo_control"] = "valor_etico"
        base["relacion_confianza"] = "confianza_condicional"
    if any(w in q for w in ("rapido", "velocidad", "tiempo real", "latencia")):
        base["velocidad_respuesta"] = "inmediata"
    if any(w in q for w in ("escala", "masivo", "millones")):
        base["escala_operacion"] = "global_masivo"
    if any(w in q for w in ("creativ", "innovacion", "disruptiv", "nuevo")):
        base["tipo_innovacion"] = "disruptiva"
    if any(w in q for w in ("futuro", "tendencia", "proyeccion")):
        base["orientacion_temporal"] = "largo_plazo"

    return base


def diverge(carto: dict[str, Any], rupture: dict[str, Any], selected: dict[str, Any], methods: list[Any], query: str) -> list[Any]:
    """Phase 3 (Divergir). Query-driven, deterministic, two-layer:
    OPERATORS generate candidates via PAIRWISE recombination (combinatorial
    divergence over 15 causal axes). CAUSAL VARIABLES measure real divergence.
    CCA flags cosmetic (no-axis-moved) candidates.

    Each idea is anchored to specific query elements, a concrete rupture,
    a concrete operator, and a concrete method.
    """
    from itertools import combinations
    ideas = []
    base = _build_dynamic_base(query)

    # Extract context from cartograph
    domain = carto.get("domain", "general")
    key_concepts = carto.get("key_concepts", [])
    actors = carto.get("actors", [])
    # Support legacy singular "actor" field
    if not actors and carto.get("actor"):
        actors = [carto["actor"]]
    # Propagate actor to base causal vector
    if actors:
        base["quien_decide"] = actors[0]
    assets = carto.get("assets", [])
    opportunities = carto.get("opportunities", [])
    assumptions = carto.get("assumptions", [])

    seq = 0
    pairs = list(combinations(methods, 2)) or [(methods[0], methods[0])]
    for (ma, mb) in pairs:
        for extreme in (False, True):
            seq += 1
            cv = _apply_family(ma["family"], dict(base), extreme)
            cv = _apply_family(mb["family"], cv, extreme)
            moved = [k for k in _CAUSAL_AXES if cv[k] != base[k]]
            divergence_real = len(moved) >= 1

            fam_a, fam_b = ma["family"], mb["family"]
            lead = fam_a if fam_a in _VALID_MECH else "capability_proof"
            mech_pair = f"{fam_a}+{fam_b}"

            # --- Query-anchored description ---
            anchor = key_concepts[0] if key_concepts else "el problema"
            actor = actors[0] if actors else "el sistema"
            asset = assets[0] if assets else "el recurso"

            if extreme:
                description = (
                    f"Aplicar {ma['name']} de forma extrema sobre '{anchor}': "
                    f"{ma.get('selection_reason', '')}. "
                    f"Luego cruzar con {mb['name']} para alterar los ejes {moved}. "
                    f"Resultado: {cv.get(moved[0], 'cambio')} cuando {moved[0]}."
                )
            else:
                description = (
                    f"Combinar {ma['name']} con {mb['name']} sobre '{anchor}': "
                    f"{ma.get('selection_reason', '')} + {mb.get('selection_reason', '')}. "
                    f"Muta ejes {moved} del dominio {domain}."
                )

            # --- Traceability fields ---
            query_anchor = anchor
            broken_assumption = assumptions[seq % len(assumptions)] if assumptions else "supuesto genérico"
            known_element = carto.get("known_space", ["enfoque estándar"])[seq % max(1, len(carto.get("known_space", [1])))]
            opportunity = opportunities[seq % len(opportunities)] if opportunities else "oportunidad no explorada"

            # --- Mechanism explanation ---
            ax_changed = moved[0] if moved else "ninguno"
            mechanism = (
                f"Al aplicar {fam_a} se modifica '{ax_changed}': "
                f"'{base.get(ax_changed, '?')}' → '{cv.get(ax_changed, '?')}'. "
                f"Al cruzar con {fam_b}, se añade '{moved[1] if len(moved) > 1 else ax_changed}'. "
                f"Esto crea una configuración causal que no existía en el espacio conocido."
            )

            # --- Expected effect ---
            expected_effect = (
                f"Al cambiar {', '.join(moved)} se produce una alternativa "
                f"al enfoque estándar de {domain}: {opportunity}"
            )

            # --- Difference signature ---
            diff_values = [f"{k}:{base[k]}→{cv[k]}" for k in moved]
            difference_signature = f"({'|'.join(diff_values)})"

            genome = {
                "actor": [base["quien_decide"]],
                "mechanism": [lead],
                "topology": [cv["topologia"]],
                "trust_model": ["evidence_based" if ("evidencia" in cv["evidencia_requerida"]) else "implicit"],
                "time_model": ["ephemeral_per_operation" if "ephemeral" in cv["topologia"] else "staged"],
            }
            g, _ = normalize_proposal(dict(genome), source_idea=f"I{seq:02d}")

            idea = {
                "id": f"I{seq:02d}",
                "title": f"{ma['name']} × {mb['name']} sobre '{anchor}' ({'extremo' if extreme else 'cruce'})",
                "description": description,
                "mechanism_causal": mechanism,
                "causal_variables": cv,
                "difference_from_known": f"Frente a '{known_element}', cambia: {', '.join(moved) or 'nada'}.",
                "genome": g.model_dump(),
                "evidence": {"field": "mechanism", "value": mech_pair, "evidence_span": f"cruce {ma['name']}×{mb['name']}"},
                "family": fam_a,
                "family2": fam_b,
                "divergence_real": divergence_real,
                "extreme": extreme,
                "causal_claim": "MECHANISM_VERIFIED",
                "duplicate_status": "candidate",
                "source_method": f"{ma['id']}+{mb['id']}",
                "method1_name": ma['name'],
                "method2_name": mb['name'],
                "method1_desc": ma.get('selection_reason', ''),
                "method2_desc": mb.get('selection_reason', ''),
                # --- Traceability ---
                "query_anchor": query_anchor,
                "domain": domain,
                "known_space_element": known_element,
                "broken_assumption": broken_assumption,
                "rupture": f"{ma['name']} + {mb['name']}",
                "method": f"{ma['id']}+{mb['id']}",
                "operator": f"{fam_a}+{fam_b}",
                "causal_axes_changed": moved,
                "mechanism_explanation": mechanism,
                "expected_effect": expected_effect,
                "difference_signature": difference_signature,
            }
            ideas.append(idea)
    return ideas


def cross_consistency_assessment(ideas: list[Any]) -> tuple[list[Any], int]:
    """CCA filter: mark cosmetic candidates (no causal axis moved) and drop them
    from the divergent set so they never count as real innovation."""
    real = []
    cosmetic = 0
    for i in ideas:
        if i.get("divergence_real"):
            real.append(i)
        else:
            i["duplicate_status"] = "cosmetic"
            cosmetic += 1
    return real, cosmetic


# ---------------------------------------------------------------------------
# Duplicate detection (condition 6/7) — uses criba.similarity
# ---------------------------------------------------------------------------
def _detect_duplicates(ideas: list[Any]) -> list[dict[str, Any]]:
    """Detect duplicates using changed_axes comparison.
    Two ideas are duplicates only if they change the SAME axes with SIMILAR values."""
    report: list[dict[str, Any]] = []
    seen: list[Any] = []
    for idea in ideas:
        cv = idea.get("causal_variables", {})
        axes_changed = set(idea.get("causal_axes_changed", []))
        matched = None
        for prev in seen:
            prev_cv = prev.get("causal_variables", {})
            prev_axes = set(prev.get("causal_axes_changed", []))
            # Same axes changed?
            if axes_changed == prev_axes:
                # Same axes changed -> check if values are similar
                same_values = sum(1 for k in axes_changed if cv.get(k) == prev_cv.get(k))
                if same_values >= len(axes_changed) - 1:  # at most 1 value differs
                    matched = {"verdict": "probable_duplicate", "similarity": 0.95,
                               "reason": f"mismos ejes {axes_changed} con valores casi idénticos"}
                    break
            # Overlapping axes (share at least 1 axis)
            overlap = axes_changed & prev_axes
            if len(overlap) >= 1 and matched is None:
                # Check if the non-overlapping axes are also similar
                diff_axes = axes_changed.symmetric_difference(prev_axes)
                if len(diff_axes) <= 2:
                    matched = {"verdict": "close_variant", "similarity": 0.75,
                               "reason": f"comparten ejes {sorted(overlap)}, difieren en {sorted(diff_axes)}"}
        if matched:
            idea["duplicate_status"] = "duplicate" if matched["verdict"] == "probable_duplicate" else "variant"
            report.append({
                "idea_id": idea["id"], "verdict": matched["verdict"],
                "similarity": matched["similarity"], "reason": matched["reason"],
                "vs": prev["id"] if matched else None,
            })
        else:
            idea["duplicate_status"] = "distinct"
            report.append({"idea_id": idea["id"], "verdict": "distinct", "similarity": 1.0, "reason": "primera de su clase"})
        seen.append(idea)
    return report


# ---------------------------------------------------------------------------
# Convergence layer (SPEC): evaluates quality of what GENERATION produced,
# using criteria derived from the operator's content. Does NOT use causal
# variables (measurement axes) as generators. Novelty is read FROM the
# measurement layer (how many distinct axes the operator moved), never
# redefined as a design axis.
# ---------------------------------------------------------------------------
_BASE_VALUES = {
    "quien_decide": "operador humano",
    "cuando": "despues de validar",
    "evidencia_requerida": "reglas estaticas",
    "si_falla": "incidente detectado tarde",
    "topologia": "centralizada",
    "fuente_poder": "jerarquia formal",
    "mecanismo_control": "reglas escritas",
    "flujo_informacion": "lineal_arriba_abajo",
    "recurso_principal": "datos_y_codigo",
    "relacion_confianza": "confianza_ciega",
    "escala_operacion": "una_organizacion",
    "velocidad_respuesta": "lenta_reactiva",
    "nivel_abstraccion": "implementacion_detallada",
    "orientacion_temporal": "corto_plazo",
    "tipo_innovacion": "incremental",
}


class ValueScoreError(ValueError):
    """Raised when value_score inputs violate the ratified contract.

    The formula value_score = evidence * novelty / cost is ratified and must not
    change. This guards its domain: cost must be strictly positive and all inputs
    finite, so the score is never silently coerced, infinite, or NaN.
    """


def value_score(evidence: float, novelty: float, cost: float) -> float:
    """Ratified convergence score: ``evidence * novelty / cost``.

    Args:
        evidence: Evidence anchoring of the idea (finite number).
        novelty: Measurement-layer novelty (finite number).
        cost: Effort to test the idea. MUST be strictly positive.

    Returns:
        The rounded value score (4 decimals).

    Raises:
        ValueScoreError: if ``cost <= 0`` or any input is non-finite. The error
            is explicit — cost is never silently converted and the result is
            never infinite or NaN.
    """
    import math as _math
    for name, val in (("evidence", evidence), ("novelty", novelty), ("cost", cost)):
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            raise ValueScoreError(f"value_score: {name} debe ser numérico, no {type(val).__name__}.")
        if not _math.isfinite(val):
            raise ValueScoreError(f"value_score: {name} debe ser finito; se recibió {val!r}.")
    if cost <= 0:
        raise ValueScoreError(
            f"value_score: cost debe ser > 0 (fórmula evidence*novelty/cost); se recibió cost={cost!r}."
        )
    return round((evidence * novelty) / cost, 4)


def _evaluate_idea(idea: dict[str, Any]) -> dict[str, Any]:
    """Convergence scoring with CONTENT-based diversity.

    Scoring now depends on:
    1. Causal variables (original)
    2. Method names (new) - longer names = more specific = higher novelty
    3. Method descriptions (new) - more detail = higher evidence
    4. Combination uniqueness (new) - different families = higher novelty
    """

    cv = idea.get("causal_variables", {})
    method1_name = idea.get("method1_name", "")
    method2_name = idea.get("method2_name", "")
    method1_desc = idea.get("method1_desc", "")
    method2_desc = idea.get("method2_desc", "")
    fam_a = idea.get("family", "")
    fam_b = idea.get("family2", "")

    # NOVELTY: basada en contenido de métodos + ejes movidos
    moved_axes = [k for k in _CAUSAL_AXES if cv.get(k) != _BASE_VALUES.get(k)]

    # Si no hay ejes movidos, novelty es 0 (regla original)
    if len(moved_axes) == 0:
        novelty = 0.0
    else:
        # Factor 1: ejes movidos (original)
        axes_novelty = len(moved_axes) / len(_CAUSAL_AXES)

        # Factor 2: diversidad de nombres (nombres más largos = más específicos)
        name_diversity = (len(method1_name) + len(method2_name)) / 200  # normalizado

        # Factor 3: si las familias son diferentes
        family_diversity = 0.2 if fam_a != fam_b else 0.0

        novelty = round(min(1.0, axes_novelty * 0.5 + name_diversity * 0.3 + family_diversity + 0.2), 4)

    # EVIDENCE: basada en descripciones + ejes concretos
    concrete = sum(1 for k in _CAUSAL_AXES if cv.get(k) and cv.get(k) != _BASE_VALUES.get(k))

    # Factor 1: ejes concretos (original)
    axes_evidence = concrete / len(_CAUSAL_AXES)

    # Factor 2: longitud de descripciones (más detalle = más evidencia)
    desc_evidence = min(1.0, (len(method1_desc) + len(method2_desc)) / 400)

    evidence = round(0.3 + 0.7 * (axes_evidence * 0.6 + desc_evidence * 0.4), 4)

    # VIABILITY
    extreme = bool(idea.get("extreme"))
    viability = round(0.45 if extreme else 0.8, 4)

    # COST
    cost = round(0.3 + (0.4 if extreme else 0.0) + 0.3 * novelty, 4)

    # SCORE
    score = value_score(evidence, novelty, cost)

    return {
        "novelty": novelty,
        "evidence": evidence,
        "viability": viability,
        "cost": cost,
        "value_score": score,
    }


# ---------------------------------------------------------------------------
# Morphological frame (debate ejes adicionales — aditivo, retrocompatible)
# ---------------------------------------------------------------------------
# 9 ejes morfológicos del debate: meta-atributos del problema/contexto.
_MORPHO_AXES: dict[str, list[str]] = {
    "actor": ["usuario", "desarrollador", "agente IA", "sistema/dato",
              "auditor", "adversario", "tercero afectado", "actor no humano",
              "agente local", "multi-agente", "humano+IA", "hardware"],
    "entrada": ["prompt", "código", "logs", "evidencia", "evento",
                "contradicción", "fallo real", "señal externa",
                "voz", "sensores", "Kanban", "clima"],
    "restriccion": ["coste cero", "offline", "hardware limitado", "tiempo extremo",
                    "datos mínimos", "confianza cero", "solo reversible",
                    "sin autoridad central", "8 GB RAM", "sin GPU", "solo terminal"],
    "salida": ["idea", "arquitectura", "mecanismo", "test", "experimento",
               "política/gate", "contraejemplo", "prototipo",
               "código", "automatización", "invento físico", "prompt reutilizable"],
    "dominio_externo": ["biología", "física", "ecología", "industria", "derecho",
                        "economía", "música/arte", "ajedrez/juegos",
                        "ciclismo", "electrónica DIY", "TRIZ", "biomimética"],
    "escala": ["componente", "aplicación", "proyecto", "equipo",
               "organización", "ecosistema"],
    "tiempo": ["instantáneo", "una sesión", "una iteración",
               "ciclo de vida", "años", "generaciones"],
    "grado_ruptura": ["conservador", "moderado", "fuerte", "absurdo-productivo"],
    "orientacion": ["prevención", "detección", "resistencia", "recuperación", "evolución"],
}

_MORPHO_DEFAULTS: dict[str, str] = {
    "actor": "desarrollador", "entrada": "prompt", "restriccion": "hardware limitado",
    "salida": "idea", "dominio_externo": "biología", "escala": "proyecto",
    "tiempo": "una sesión", "grado_ruptura": "moderado", "orientacion": "detección",
}

_MORPHO_SIGNALS: list[tuple[tuple[str, ...], str, str]] = [
    (("usuario", "user", "cliente", "end user"),                "actor", "usuario"),
    (("agente", "agent", "ia", "llm", "bot"),                   "actor", "agente IA"),
    (("adversario", "atacante", "hacker", "threat"),            "actor", "adversario"),
    (("auditor", "revisor", "inspector"),                       "actor", "auditor"),
    (("multi", "team", "equipo", "colectivo"),                  "actor", "multi-agente"),
    (("código", "code", "script", "fichero"),                   "entrada", "código"),
    (("log", "logs", "traza", "trace"),                         "entrada", "logs"),
    (("evento", "event", "trigger", "alarma"),                  "entrada", "evento"),
    (("voz", "audio", "speech"),                                "entrada", "voz"),
    (("sensor", "iot", "hardware"),                             "entrada", "sensores"),
    (("fallo", "error", "bug", "crash"),                        "entrada", "fallo real"),
    (("gratis", "gratuito", "free", "sin costo", "coste cero"), "restriccion", "coste cero"),
    (("offline", "sin red", "sin internet", "local"),           "restriccion", "offline"),
    (("rápido", "urgente", "inmediato", "tiempo extremo"),      "restriccion", "tiempo extremo"),
    (("pocos datos", "escasos", "mínimos datos"),               "restriccion", "datos mínimos"),
    (("sin gpu", "cpu only", "bajo recurso"),                   "restriccion", "sin GPU"),
    (("idea", "concepto", "propuesta"),                         "salida", "idea"),
    (("arquitectura", "diseño", "blueprint"),                   "salida", "arquitectura"),
    (("test", "prueba", "experimento", "hipótesis"),            "salida", "test"),
    (("prototipo", "mvp", "demo"),                              "salida", "prototipo"),
    (("biolog", "celula", "adn", "evolución"),                  "dominio_externo", "biología"),
    (("física", "mecánica", "termodinámica"),                   "dominio_externo", "física"),
    (("ecolog", "ecosistema", "sostenib"),                      "dominio_externo", "ecología"),
    (("juego", "chess", "ajedrez", "game"),                     "dominio_externo", "ajedrez/juegos"),
    (("triz", "inventive", "altshuller"),                       "dominio_externo", "TRIZ"),
    (("biomimética", "biomimicry", "nature"),                   "dominio_externo", "biomimética"),
    (("componente", "función", "módulo pequeño"),               "escala", "componente"),
    (("aplicación", "app", "servicio"),                         "escala", "aplicación"),
    (("equipo", "team", "squad"),                               "escala", "equipo"),
    (("organización", "empresa", "corporación"),                "escala", "organización"),
    (("ecosistema", "industria", "sector", "mercado"),          "escala", "ecosistema"),
    (("instantáneo", "tiempo real", "real-time"),               "tiempo", "instantáneo"),
    (("sesión", "session", "conversación"),                     "tiempo", "una sesión"),
    (("ciclo", "sprint", "iteración"),                          "tiempo", "una iteración"),
    (("año", "largo plazo", "long term"),                       "tiempo", "años"),
    (("incremental", "mejora", "optimiza", "refactor"),         "grado_ruptura", "conservador"),
    (("ruptura", "disrupt", "radical", "nuevo paradigma"),      "grado_ruptura", "fuerte"),
    (("absurdo", "imposible", "utópico"),                       "grado_ruptura", "absurdo-productivo"),
    (("prevención", "prevent", "evitar"),                       "orientacion", "prevención"),
    (("detectar", "monitor", "detect"),                         "orientacion", "detección"),
    (("resilient", "tolerancia", "resistencia"),                "orientacion", "resistencia"),
    (("recuperar", "recover", "restaurar"),                     "orientacion", "recuperación"),
    (("evolución", "aprendizaje", "adapt"),                     "orientacion", "evolución"),
    (("seguridad", "security", "protect", "defensa"),           "orientacion", "prevención"),
    (("hack", "pentest", "ataque", "exploit"),                  "orientacion", "detección"),
]


def build_morpho_frame(query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Infiere los valores morfológicos más probables para la query dada.

    Retrocompatible: campo nuevo ``morphological_frame`` en el packet.
    Nunca altera campos existentes.
    """
    text = query.lower() + " " + (json.dumps(context or {}).lower())
    frame: dict[str, str] = dict(_MORPHO_DEFAULTS)
    evidence: dict[str, list[str]] = {ax: [] for ax in _MORPHO_AXES}
    for keywords, axis, value in _MORPHO_SIGNALS:
        for kw in keywords:
            if kw in text:
                if not evidence[axis]:
                    frame[axis] = value
                evidence[axis].append(kw)
                break
    return {
        "schema": "morphological_frame_v1",
        "inferred": frame,
        "evidence": {ax: evs[:3] for ax, evs in evidence.items() if evs},
        "coverage": f"{sum(1 for v in evidence.values() if v)}/{len(_MORPHO_AXES)} ejes con evidencia",
    }


# ---------------------------------------------------------------------------
# Orchestration (condition 2/3/10/11)
# ---------------------------------------------------------------------------
def activate(query: str, current: str = "auto", mode: str = "balanced", supporting_methods: int = 12,
             context: dict[str, Any] | None = None, safety_level: str = "strict", manual_methods: list[str] | None = None,
             cartograph_fn: CartographFn | None = None, diverge_fn: DivergeFn | None = None) -> dict[str, Any]:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("La consulta no puede estar vacía.")
    if len(query) > MAX_QUERY_CHARS:
        raise ValueError(f"La consulta excede el límite de {MAX_QUERY_CHARS} caracteres.")
    if mode not in VALID_MODES:
        raise ValueError(f"Modo inválido: {mode}")
    if safety_level not in {"strict", "standard"}:
        raise ValueError("safety_level debe ser strict o standard.")

    context = context or {}

    # --- HIPERMEGAPROMPT context_layer_v2 (optional, flag-gated) ---
    if FEATURES.get("context_layer_v2"):
        try:
            from .context_layer import build_context
            _hcm_ctx = build_context(query, context, mode="criba", selection=None)
            context["hcm_context"] = _hcm_ctx.model_dump()
        except Exception:
            pass  # Graceful degradation: context_layer never blocks the engine

    selection = select(query, current)
    selected = find_current(selection["selected_current"])
    methods = select_methods(supporting_methods, mode, manual_methods, query=query)

    carto = (cartograph_fn or cartograph_and_break)(query, context, selection.__dict__ if hasattr(selection, "__dict__") else selection)
    rupture = {
        "operations": carto["ruptures"],
        "broken_assumptions": [r["assumption_id"] for r in carto["ruptures"] if r["operation"] == "invert"],
        "inversions": [r["result"] for r in carto["ruptures"] if r["operation"] == "invert"],
        "eliminations": [r["result"] for r in carto["ruptures"] if r["operation"] == "eliminate"],
        "counterexample": carto["counterexample"],
    }
    ideas = (diverge_fn or diverge)(carto, rupture, selected, methods, query)
    # CCA: drop cosmetic candidates (operators that moved no causal axis).
    real_ideas, cosmetic_count = cross_consistency_assessment(ideas)
    duplicate_report = _detect_duplicates(real_ideas)

    # Deduplicación limpia: excluir probable_duplicates, luego fallback a top 8
    kept = [i for i, r in zip(real_ideas, duplicate_report) if r["verdict"] != "probable_duplicate"]

    # Si no hay suficientes ideas únicas, tomar las mejores sin duplicados
    if len(kept) < 8:
        seen_ids = set(i["id"] for i in kept)
        for i in real_ideas:
            if len(kept) >= 8:
                break
            if i["id"] not in seen_ids:
                kept.append(i)
                seen_ids.add(i["id"])

    families = sorted({i["family"] for i in kept})
    unclassified = []
    for i in kept:
        for up in i["genome"].get("unclassified_properties", []):
            unclassified.append(up if isinstance(up, dict) else up.model_dump())
    real_divergent = sum(1 for i in kept if i.get("divergence_real"))

    # Convergence layer: score each kept idea (operator-produced content) and rank.
    for i in kept:
        i["convergence"] = _evaluate_idea(i)
    ranked = sorted(kept, key=lambda x: x["convergence"]["value_score"], reverse=True)
    kept[:] = ranked
    top_ideas = [i["id"] for i in kept[:3]]
    mean_value = round(sum(i["convergence"]["value_score"] for i in kept) / max(1, len(kept)), 4)

    # --- Interprete-serendipia (capa P2): interpretación epistemológica ---
    # Flag-gate (FEATURES["interprete_serendipia"]): NO afecta el packet base
    # en modo clásico; solo añade el bloque innovation.interprete.
    interprete_block: dict[str, Any] = {"applied": False}
    if FEATURES.get("interprete_serendipia"):
        try:
            api_key = context.get("zai_api_key") if isinstance(context, dict) else None
            from criba.constants import DEFAULT_DB
            from criba.storage import Storage
            juez = JuezInterprete(api_key=api_key, storage=Storage(context.get("database", DEFAULT_DB)) if isinstance(context, dict) and "database" in context else None)
            interp_result = juez.interpretar_lote(
                query=query, ideas=kept, activation_id=str(uuid.uuid4()),
                run_id=f"interprete-{uuid.uuid4().hex[:8]}", seed=context.get("seed") if isinstance(context, dict) else None,
            )
            interprete_block = {
                "applied": True,
                "modelo": interp_result["modelo"],
                "fallback_usado": interp_result["fallback_usado"],
                "interpretados": [
                    {"idea_id": r["id"],
                     "labels": r.get("interprete_labels", []),
                     "score": r.get("interprete_score", 0.0),
                     "veredicto": r.get("interprete_verdict", "PENDIENTE"),
                     "dh": r.get("prefilter", {}).get("dh"),
                     "registro": r.get("_registro", {}).get("status"),
                    }
                    for r in interp_result["interpretados"]
                ],
                "prefiltrado_stats": interp_result["prefiltrado"]["stats"],
                "top_interprete": interp_result["interpretados"][0] if interp_result["interpretados"] else None,
            }
        except Exception:
            interprete_block = {"applied": True, "error": "interprete_no_disponible"}

    innovation: dict[str, Any] = {
        "known_space": carto["known_space"],
        "saturated_mechanisms": carto["saturated_mechanisms"],
        "assumptions": carto["assumptions"],
        "ruptures": carto["ruptures"],
        "idea_families": families,
        "ideas": kept,  # <-- canonical collection
        "real_divergent_count": real_divergent,
        "cosmetic_rejected": cosmetic_count,
        "top_ideas": top_ideas,
        "mean_value_score": mean_value,
        "duplicate_report": [r for r in duplicate_report if r["verdict"] != "probable_duplicate"],
        "unclassified_properties": unclassified,
    }

    # HIPERMEGAPROMPT context_layer_v2: attach structured context to output
    if FEATURES.get("context_layer_v2") and "hcm_context" in context:
        innovation["hcm_context"] = context["hcm_context"]

    # Adjunto el bloque interprete-serendipia al innovation block (capa P2).
    innovation["interprete"] = interprete_block

    metrics = {
        "potential_novelty": _clamp(60 + real_divergent * 4 + (10 if carto.get("wants_novelty") else 0)),
        "divergence": _clamp(40 + 12 * min(real_divergent, 8)),
        "feasibility": _clamp(60 + (8 if safety_level == "standard" else 0)),
        "controlled_risk": _clamp(48 - (6 if safety_level == "strict" else 0)),
        "reversibility": _clamp(74),
        "uncertainty": _clamp(56),
        # Rule 9 (Comet): differentiated confidence.
        # conf_code_executes: verifiable by reading the code (family->axis->value map exists).
        # conf_causal_root: requires a counterfactual test (change X, see if Y changes);
        #   in the LOCAL_MVP this is INFERRED, not proven, so it is flagged explicitly.
        "conf_code_executes": 1.0,
        "conf_causal_root": "INFERRED_NOT_PROVEN",
        "mean_value_score": mean_value,
    }
    # FASE 0 — alternativa C (ratificada por humano). Separa dos dimensiones que
    # el motor mezclaba:
    #  - pipeline_action: que hacer DESPUES (PROTOTIPAR / DIVERGIR). Basado solo en
    #    el numero de familias, es deliberadamente conservador y NO autoriza ADOPTAR.
    #  - recommended_status: estado de la idea, SIEMPRE en VALID_DECISIONS. Con la
    #    evidencia actual (solo numero de familias) no se justifica ADOPTAR, asi que
    #    se fija en "AMPLIAR PRUEBA" hasta que exista una regla explicita y probada.
    # La formula de convergencia (value_score = evidence*novelty/cost) queda intacta.
    pipeline_action = "PROTOTIPAR" if len(families) >= 4 else "DIVERGIR"
    if pipeline_action not in VALID_PIPELINE_ACTIONS:
        raise ValueError(f"pipeline_action fuera de enum: {pipeline_action}")
    recommended_status = "AMPLIAR PRUEBA"  # miembro de VALID_DECISIONS
    if recommended_status not in VALID_DECISIONS:
        raise ValueError(f"recommended_status fuera de enum: {recommended_status}")
    decision = {
        "pipeline_action": pipeline_action,
        "recommended_status": recommended_status,
        "justification": f"{len(families)} familias representadas; {metrics['divergence']}/100 de divergencia. {pipeline_action}: lleva la idea a prototipo en sombra.",
        "confidence": round(min(0.85, 0.4 + metrics["potential_novelty"] / 250 + metrics["divergence"] / 400), 2),
    }

    packet: dict[str, Any] = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "packet_type": "MANDATORY_MODEL_PACKET",
        "activation_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "intent": "INNOVAR",
        "versions": {"currents": CURRENT_CATALOG_VERSION, "selector": SELECTOR_VERSION, "genome": ONTOLOGY_VERSION},
        "original_query": query,
        "selected_current": {"id": selected["id"], "name": selected["name"], "score": selection["score"],
                              "selection_reasons": selection["selection_reasons"]},
        "supporting_methods": [{"id": m["id"], "name": m["name"], "family": m["family"],
                                 "axis": m.get("axis", ""), "sector": m.get("sector", ""),
                                 "reason": m["reason"]} for m in methods],
        "contextualization": {"problem": query.strip(), "known_space": carto["known_space"],
                               "assumptions": carto["assumptions"], "saturated_mechanisms": carto["saturated_mechanisms"]},
        "rupture": rupture,
        "innovation": innovation,
        "experiment": {"falsifiable_hypothesis": f"La variante basada en {selected['name']} abre ideas nuevas sin romper guardrails.",
                        "baseline": "Lo ya conocido.", "variant": kept[0]["description"] if kept else "",
                        "damage_limit": "Solo datos sintéticos; cero cambios en proyectos reales.",
                        "sandbox": "Entorno local temporal, aislado y sin credenciales ni red externa.",
                        "rollback": "Eliminar artefactos temporales y conservar el registro de evidencia."},
        "metrics": metrics,
        "decision": decision,
        "model_instruction": INSTRUCTION.format(current=selected["name"]),
        "response_contract": {"must_use_packet": True, "must_name_current": True,
                               "must_generate_new_ideas": True, "must_state_uncertainty": True,
                               "must_not_reveal_private_chain_of_thought": True},
        "security": {"safety_level": safety_level, "no_command_execution": True,
                     "no_network_by_default": True, "no_credentials_access": True},
    }
    # condition 3: packet["ideas"] is the SAME object as innovation["ideas"] (no divergence possible)
    packet["ideas"] = packet["innovation"]["ideas"]
    # Morphological frame — aditivo, nunca bloquea
    try:
        packet["morphological_frame"] = build_morpho_frame(query, context)
    except Exception:  # noqa: BLE001
        pass  # Graceful degradation: morpho frame nunca bloquea el engine
    if mode == "minimal":
        packet["minimal_summary"] = {"current": selected["name"], "intent": "INNOVAR",
                                     "central_idea": kept[0]["description"] if kept else "", "decision": decision}
    if FEATURES.get("compound_personas"):
        # P2 is additive and intentionally stops before P3 synthesis.  The
        # first-pass personas share only this completed packet, never each
        # other's output.  Divergent recommendations remain explicitly
        # awaiting a minority-preserving synthesis instead of being collapsed.
        from .personas import (
            DEFAULT_TEAM_PROTOCOL,
            evaluate_persona_diversity,
            run_personas,
            validate_team_protocol,
        )

        persona_results = run_personas(packet)
        diversity = evaluate_persona_diversity(persona_results)
        protocol = validate_team_protocol(persona_results)
        if not diversity.is_diverse:
            persona_status = "REJECTED_REGEN_REQUIRED"
        elif protocol.requires_minority_report:
            persona_status = "AWAITING_P3_SYNTHESIS"
        else:
            persona_status = "READY"
        packet["persona_analysis"] = {
            "schema_version": "1.0.0",
            "status": persona_status,
            "team_protocol": DEFAULT_TEAM_PROTOCOL.model_dump(mode="json"),
            "diversity": diversity.model_dump(mode="json"),
            "protocol_validation": protocol.model_dump(mode="json"),
            "results": [result.model_dump(mode="json") for result in persona_results],
        }
    return packet


def _clamp(v: int) -> int:
    return max(0, min(100, v))


def export_innovation_portfolio(packet: dict[str, Any]) -> dict[str, Any]:
    """INNOVATION_PORTFOLIO_PACKET is ONLY an exported view, never a persisted model."""
    inv = packet.get("innovation", {})
    return {
        "view": "innovation_portfolio",
        "activation_id": packet.get("activation_id"),
        "original_query": packet.get("original_query"),
        "known_space": inv.get("known_space"),
        "saturated_mechanisms": inv.get("saturated_mechanisms"),
        "assumptions": inv.get("assumptions"),
        "ruptures": inv.get("ruptures"),
        "idea_families": inv.get("idea_families"),
        "ideas": inv.get("ideas"),
        "duplicate_report": inv.get("duplicate_report"),
        "unclassified_properties": inv.get("unclassified_properties"),
    }


def build_prompt(packet: dict[str, Any]) -> str:
    return "\n\n".join([
        "# Consulta original\n" + packet["original_query"],
        "# Intención CRIBA\n" + packet.get("intent", "INNOVAR"),
        "# Instrucción CRIBA\n" + packet["model_instruction"],
        "# MANDATORY_MODEL_PACKET\n" + json.dumps(packet, ensure_ascii=False, indent=2),
        "# Contrato\nUsa obligatoriamente el paquete para generar ideas nuevas; no reveles razonamiento privado.",
    ])


def activate_with_llm(query: str, current: str = "auto", mode: str = "balanced",
                      supporting_methods: int = 8, context: dict[str, Any] | None = None,
                      safety_level: str = "strict", manual_methods: list[str] | None = None,
                      llm_mode: str = "none", llm_kwargs: dict[str, Any] | None = None) -> dict[str, Any]:
    """Activación de CRIBA con soporte LLM opcional.

    Args:
        llm_mode: "none" (determinista), "offline" (Ollama), "cloud" (API)
        llm_kwargs: Parámetros adicionales para el backend LLM
    """
    # Primero ejecutar el motor determinista para obtener el packet base
    packet = activate(query, current, mode, supporting_methods, context,
                      safety_level, manual_methods)

    # Si no se requiere LLM, retornar el packet determinista
    if llm_mode == "none":
        return packet

    # Importar adaptador LLM
    from .llm_adapter import create_backend, generate_ideas_with_llm

    # Crear backend LLM
    backend = create_backend(llm_mode, **(llm_kwargs or {}))

    if not backend.is_available():
        print(f"Advertencia: Backend LLM '{llm_mode}' no disponible. Usando modo determinista.")
        return packet

    # Obtener métodos para el prompt
    methods = packet.get("supporting_methods", [])

    # Generar ideas con LLM
    try:
        llm_ideas = generate_ideas_with_llm(packet, methods, query, backend)

        # Agregar ideas LLM al packet
        if "innovation" not in packet:
            packet["innovation"] = {}
        if "ideas" not in packet["innovation"]:
            packet["innovation"]["ideas"] = []

        # Combinar ideas deterministas con LLM
        existing_ideas = packet["innovation"]["ideas"]
        packet["innovation"]["ideas"] = existing_ideas + llm_ideas

        # Actualizar métricas
        total_ideas = len(packet["innovation"]["ideas"])
        packet["innovation"]["llm_ideas_count"] = len(llm_ideas)
        packet["innovation"]["deterministic_ideas_count"] = len(existing_ideas)

        # Actualizar packet principal
        packet["ideas"] = packet["innovation"]["ideas"]
        packet["llm_mode"] = llm_mode

    except Exception as e:
        print(f"Advertencia: Error generando ideas con LLM: {e}")
        print("Continuando con ideas deterministas.")

    return packet
