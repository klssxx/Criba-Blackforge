"""12 Ejes Ortogonales de BlackForge Orthogonal.

Catálogo inmutable: cada eje representa una dimensión estructural independiente
del espacio de ideas. Las ideas se clasifican por qué valor toma en cada eje,
permitiendo detectar regiones no exploradas y guiar la búsqueda.

Ejes:
    AX-01 TRANSFORMACION    — Qué operación se realiza
    AX-02 OBJETO            — Qué cosa se transforma
    AX-03 PERSPECTIVA       — Desde quién observa
    AX-04 ESCALA            — Tamaño/granularidad
    AX-05 TIEMPO            — Dimensión temporal
    AX-06 TOPOLOGIA         — Conexión entre partes
    AX-07 CAUSALIDAD        — Modelo causa→efecto
    AX-08 INFORMACION       — Estado del conocimiento
    AX-09 RECURSOS          — Condiciones de supervivencia
    AX-10 AUTORIDAD         — Quién decide y por qué
    AX-11 EPISTEMOLOGIA     — Cómo se obtiene conclusión
    AX-12 PRESION_FALLO     — Fuerza reveladora
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Tuple


@dataclass(frozen=True)
class Axis:
    """Un eje ortogonal con sus valores posibles."""
    id: str
    name: str
    description: str
    values: Tuple[str, ...]

    def validate_value(self, value: str) -> bool:
        return value in self.values

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Axis):
            return NotImplemented
        return self.id == other.id


# ── Los 12 ejes ortogonales ──────────────────────────────────────────

AXES: Dict[str, Axis] = {
    "AX-01": Axis(
        id="AX-01",
        name="TRANSFORMACION",
        description="Qué operación se realiza sobre el objeto",
        values=(
            "INVERTIR", "ELIMINAR", "SUSTITUIR", "AÑADIR", "DIVIDIR",
            "FUSIONAR", "DESACOPLAR", "RECOMBINAR", "PERMUTAR", "DESPLAZAR",
            "COMPRIMIR", "EXPANDIR", "DUPLICAR", "ABSTRAER", "CONCRETAR",
            "RANDOMIZAR",
        ),
    ),
    "AX-02": Axis(
        id="AX-02",
        name="OBJETO",
        description="Qué cosa se transforma",
        values=(
            "OBJETIVO", "SUPUESTO", "AXIOMA", "REGLA", "DATO", "ESTADO",
            "IDENTIDAD", "PERMISO", "RECURSO", "INTERFAZ", "PROCESO",
            "COMPONENTE", "DEPENDENCIA", "METRICA", "INCENTIVO", "EVIDENCIA",
        ),
    ),
    "AX-03": Axis(
        id="AX-03",
        name="PERSPECTIVA",
        description="Desde quién/qué se observa el problema",
        values=(
            "USUARIO", "NOVATO", "EXPERTO", "MANTENEDOR", "AUDITOR",
            "ADVERSARIO", "REGULADOR", "EXCLUIDO", "TERCERO", "SUCESOR",
            "DATO", "ERROR", "COMPONENTE", "COLECTIVO", "SISTEMA", "NO-HUMANO",
        ),
    ),
    "AX-04": Axis(
        id="AX-04",
        name="ESCALA",
        description="Tamaño/granularidad del problema",
        values=(
            "EVENTO", "OPERACION", "COMPONENTE", "MODULO", "PRODUCTO",
            "ORGANIZACION", "RED", "ECOSISTEMA", "SOCIEDAD", "CIVILIZACION",
            "MICRO", "MACRO", "FRACTAL", "ENJAMBRE",
        ),
    ),
    "AX-05": Axis(
        id="AX-05",
        name="TIEMPO",
        description="Cómo se modifica la dimensión temporal",
        values=(
            "INSTANTANEO", "RETARDADO", "ANTICIPADO", "REVERSIBLE",
            "IRREVERSIBLE", "RAMIFICADO", "CIRCULAR", "MULTIRRELOJ",
            "EFIMERO", "PERSISTENTE", "RETROSPECTIVO", "PROSPECTIVO",
            "GENERACIONES",
        ),
    ),
    "AX-06": Axis(
        id="AX-06",
        name="TOPOLOGIA",
        description="Cómo están conectadas las partes",
        values=(
            "CENTRALIZADA", "DISTRIBUIDA", "JERARQUICA", "FEDERADA",
            "MODULAR", "CELULAR", "MALLA", "ESTRELLA", "CADENA", "CAPAS",
            "EDGE", "REDUNDANTE", "FRACTAL", "DESCONECTADA",
        ),
    ),
    "AX-07": Axis(
        id="AX-07",
        name="CAUSALIDAD",
        description="Qué modelo causa→efecto se emplea",
        values=(
            "DIRECTA", "MULTIPLE", "PROBABILISTICA", "CIRCULAR",
            "RETARDADA", "DISTRIBUIDA", "EMERGENTE", "CONTRAFACTUAL",
            "POR_AUSENCIA", "MEDIADA", "FEEDBACK", "CAUSA_COMUN",
        ),
    ),
    "AX-08": Axis(
        id="AX-08",
        name="INFORMACION",
        description="Qué sabe cada elemento",
        values=(
            "COMPLETA", "PARCIAL", "LOCAL", "ASIMETRICA", "RETARDADA",
            "RUIDOSA", "CONTRADICTORIA", "ADVERSARIAL", "CIFRADA",
            "COMPRIMIDA", "EFIMERA", "REDUNDANTE", "SIN_HISTORIAL",
        ),
    ),
    "AX-09": Axis(
        id="AX-09",
        name="RECURSOS_RESTRICCIONES",
        description="Bajo qué condiciones debe sobrevivir",
        values=(
            "COSTE_CERO", "DATOS_CERO", "RED_CERO", "ALMACENAMIENTO_CERO",
            "EXPERTOS_CERO", "TIEMPO_MINIMO", "HARDWARE_LIMITADO",
            "ENERGIA_LIMITADA", "RECURSO_UNICO", "ABUNDANCIA_EXTREMA",
            "SOLO_REVERSIBLE",
        ),
    ),
    "AX-10": Axis(
        id="AX-10",
        name="AUTORIDAD_INCENTIVOS",
        description="Quién decide y por qué",
        values=(
            "CENTRAL", "DISTRIBUIDA", "ROTATIVA", "DELEGADA", "REVOCABLE",
            "VETO", "CONSENSO", "MERCADO", "REPUTACION", "COMPETENCIA",
            "COOPERACION", "SEPARACION_PODERES", "SIN_AUTORIDAD",
        ),
    ),
    "AX-11": Axis(
        id="AX-11",
        name="EPISTEMOLOGIA",
        description="Cómo se obtiene una conclusión",
        values=(
            "PRIMEROS_PRINCIPIOS", "INDUCCION", "DEDUCCION", "ABDUCCION",
            "BAYESIANO", "FALSACION", "DIALECTICA", "CAUSAL",
            "PROBABILISTICO", "FORMAL", "EXPERIMENTAL", "CONTRAFACTUAL",
            "ANALOGIA",
        ),
    ),
    "AX-12": Axis(
        id="AX-12",
        name="PRESION_FALLO",
        description="Qué fuerza intenta revelar algo nuevo",
        values=(
            "ERROR_HONESTO", "ADVERSARIO", "INSIDER", "COLUSION",
            "DERIVA", "CORRUPCION_SILENCIOSA", "FALLO_COMUN", "MONOCULTURA",
            "MIGRACION", "VERSION_INCOMPATIBLE", "COMPORTAMIENTO_INDEFINIDO",
            "RARE_EVENT", "OOD",
        ),
    ),
}

# Índices derivados para búsqueda rápida
_AXIS_BY_NAME: Dict[str, Axis] = {ax.name: ax for ax in AXES.values()}
_ALL_VALUES: Dict[str, FrozenSet[str]] = {
    ax.id: frozenset(ax.values) for ax in AXES.values()
}


def get_axis(axis_id: str) -> Axis | None:
    """Devuelve un eje por su ID (AX-01..AX-12)."""
    return AXES.get(axis_id)


def get_axis_by_name(name: str) -> Axis | None:
    """Devuelve un eje por su nombre (TRANSFORMACION, OBJETO, ...)."""
    return _AXIS_BY_NAME.get(name)


def validate_coordinate(axis_id: str, value: str) -> bool:
    """Valida que un valor sea válido para un eje dado."""
    axis = AXES.get(axis_id)
    return axis.validate_value(value) if axis else False


def all_axes() -> Tuple[Axis, ...]:
    """Devuelve todos los 12 ejes en orden canónico."""
    return tuple(AXES.values())


def total_cells() -> int:
    """Número total de celdas en el espacio ortogonal (suma de valores por eje)."""
    return sum(len(ax.values) for ax in AXES.values())
