"""i18n mínimo — ES (default) / EN. Sin dependencias externas."""
from __future__ import annotations

from collections.abc import Callable

_STRINGS: dict[str, dict[str, str]] = {
    "es": {
        # nav
        "nav.nueva_idea":   "Nueva idea",
        "nav.nueva_idea.sub": "Inicia el flujo, pide el problema base",
        "nav.generar":      "Generar",
        "nav.generar.sub":  "Ejecuta los 16 operadores",
        "nav.evaluar":      "Evaluar",
        "nav.evaluar.sub":  "Ranking por value_score",
        "nav.guardar":      "Guardar",
        "nav.guardar.sub":  "Persiste la idea en el catálogo",
        "nav.actualizar":   "Actualizar innovaciones",
        "nav.actualizar.sub": "Tendencias, tecnología, diseño",
        "nav.historial":    "Historial",
        "nav.historial.sub": "Ideas generadas antes",
        "nav.blackforge":   "Blackforge",
        "nav.blackforge.sub": "Panel de control BLACKFORGE",
        # topbar
        "greeting.title":   "Hola, Innovador",
        "greeting.sub":     "Listo para transformar ideas en impacto",
        "mode.innovacion":  "MODO: INNOVACIÓN",
        "lang.btn":         "EN",
        # CRIBA main
        "motor.title":      "MOTOR DE INNOVACIÓN",
        "idea.activa":      "IDEA ACTIVA",
        "ranking.title":    "RANKING DE IDEAS",
        # BLACKFORGE
        "bf.ejecutar":      "▶  EJECUTAR GENERACIÓN",
        "bf.ejecutando":    "⟳  EJECUTANDO...",
        "bf.volver":        "← VOLVER A CRIBA",
        "bf.ver_contexto":  "VER CONTEXTO",
        "bf.estado":        "ESTADO DE BLACKFORGE",
        "bf.estado.desc":   ("Sistema listo para generar ideas de innovación en "
                             "ciberseguridad estructuradas y verificables: red team, "
                             "explotación, defensa, ingeniería social e IA & ML."),
        "bf.operativa":     "● OPERATIVA",
        "bf.modos":         "MODOS DE TRABAJO",
        "bf.ideas":         "IDEAS GENERADAS (TOP 5)",
        "bf.modelos":       "INTEGRACIÓN DE MODELOS",
        "bf.verificacion":  "VERIFICACIÓN Y TRAZABILIDAD",
        "bf.modo.optimizado":      "Modo optimizado",
        "bf.modo.optimizado.desc": "Equilibra novedad y eficacia.",
        "bf.modo.asociativa":      "Lotería asociativa",
        "bf.modo.asociativa.desc": "Combina familias y mecanismos.",
        "bf.modo.pura":            "Lotería pura",
        "bf.modo.pura.desc":       "Explora combinaciones aleatorias.",
        # tabla ideas
        "col.titulo":       "Título de la Idea",
        "col.mecanismo":    "Mecanismo Principal",
        "col.riesgo":       "Riesgo",
        "col.novedad":      "Novedad",
        "col.prioridad":    "Prioridad",
        # KPIs
        "kpi.cobertura":    "COBERTURA DE FAMILIAS",
        "kpi.cubierto":     "Cubierto",
        "kpi.integridad":   "INTEGRIDAD DEL PROCESO",
        "kpi.excelente":    "Excelente",
        "kpi.verificador":  "ESTADO DEL VERIFICADOR",
        "kpi.activo":       "● VERIFICADOR ACTIVO",
        "kpi.todo_ok":      "Todo en orden",
        # riesgo / novedad / prioridad
        "risk.low":         "Bajo",
        "risk.medium":      "Medio",
        "risk.high":        "Alto",
        "risk.critical":    "Crítico",
        "nov.alta":         "Alta",
        "nov.muy_alta":     "Muy alta",
        "nov.media":        "Media",
        "pri.critica":      "Crítica",
        "pri.alta":         "Alta",
        "pri.media":        "Media",
    },
    "en": {
        # nav
        "nav.nueva_idea":   "New idea",
        "nav.nueva_idea.sub": "Start flow, enter base problem",
        "nav.generar":      "Generate",
        "nav.generar.sub":  "Run the 16 operators",
        "nav.evaluar":      "Evaluate",
        "nav.evaluar.sub":  "Rank by value_score",
        "nav.guardar":      "Save",
        "nav.guardar.sub":  "Persist idea to catalog",
        "nav.actualizar":   "Update innovations",
        "nav.actualizar.sub": "Trends, technology, design",
        "nav.historial":    "History",
        "nav.historial.sub": "Previously generated ideas",
        "nav.blackforge":   "Blackforge",
        "nav.blackforge.sub": "BLACKFORGE control panel",
        # topbar
        "greeting.title":   "Hello, Innovator",
        "greeting.sub":     "Ready to transform ideas into impact",
        "mode.innovacion":  "MODE: INNOVATION",
        "lang.btn":         "ES",
        # CRIBA main
        "motor.title":      "INNOVATION ENGINE",
        "idea.activa":      "ACTIVE IDEA",
        "ranking.title":    "IDEA RANKING",
        # BLACKFORGE
        "bf.ejecutar":      "▶  RUN GENERATION",
        "bf.ejecutando":    "⟳  RUNNING...",
        "bf.volver":        "← BACK TO CRIBA",
        "bf.ver_contexto":  "VIEW CONTEXT",
        "bf.estado":        "BLACKFORGE STATUS",
        "bf.estado.desc":   ("System ready to generate structured, verifiable "
                             "cybersecurity innovation ideas: red team, exploitation, "
                             "defense, social engineering & AI/ML."),
        "bf.operativa":     "● OPERATIONAL",
        "bf.modos":         "WORK MODES",
        "bf.ideas":         "GENERATED IDEAS (TOP 5)",
        "bf.modelos":       "MODEL INTEGRATION",
        "bf.verificacion":  "VERIFICATION & TRACEABILITY",
        "bf.modo.optimizado":      "Optimized mode",
        "bf.modo.optimizado.desc": "Balances novelty and effectiveness.",
        "bf.modo.asociativa":      "Associative lottery",
        "bf.modo.asociativa.desc": "Combines families and mechanisms.",
        "bf.modo.pura":            "Pure lottery",
        "bf.modo.pura.desc":       "Explores random combinations.",
        # tabla ideas
        "col.titulo":       "Idea Title",
        "col.mecanismo":    "Main Mechanism",
        "col.riesgo":       "Risk",
        "col.novedad":      "Novelty",
        "col.prioridad":    "Priority",
        # KPIs
        "kpi.cobertura":    "FAMILY COVERAGE",
        "kpi.cubierto":     "Covered",
        "kpi.integridad":   "PROCESS INTEGRITY",
        "kpi.excelente":    "Excellent",
        "kpi.verificador":  "VERIFIER STATUS",
        "kpi.activo":       "● VERIFIER ACTIVE",
        "kpi.todo_ok":      "All clear",
        # riesgo / novedad / prioridad
        "risk.low":         "Low",
        "risk.medium":      "Medium",
        "risk.high":        "High",
        "risk.critical":    "Critical",
        "nov.alta":         "High",
        "nov.muy_alta":     "Very high",
        "nov.media":        "Medium",
        "pri.critica":      "Critical",
        "pri.alta":         "High",
        "pri.media":        "Medium",
    },
}

_current: str = "es"
_listeners: list[Callable[[], None]] = []


def t(key: str) -> str:
    """Devuelve el string en el idioma activo; fallback a ES, luego a la clave."""
    return (_STRINGS[_current].get(key)
            or _STRINGS["es"].get(key)
            or key)


def lang() -> str:
    return _current


def set_lang(code: str) -> None:
    global _current
    _current = code if code in _STRINGS else "es"
    for cb in _listeners:
        try:
            cb()
        except Exception:
            pass


def toggle() -> None:
    set_lang("en" if _current == "es" else "es")


def on_change(cb: Callable[[], None]) -> None:
    """Registra callback invocado en cada cambio de idioma."""
    _listeners.append(cb)
