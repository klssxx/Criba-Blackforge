"""Ficha de bloqueo (astra!.txt paso 1): el objetivo concreto de cada exploración.

Pregunta central: ¿qué relación limita hoy el resultado buscado, y qué cambio
concreto la superaría conservando las restricciones obligatorias?

Amplía la representación del problema existente: NO crea motor, catálogo ni
almacén nuevo. La ficha viaja al intérprete dentro del cruce (idea["bloqueo"])
y queda registrada en la ficha de invención para trazabilidad.

Distinciones epistémicas obligatorias (ASTRA §3): el ORIGEN de cada pieza de
evidencia se declara — hecho / hipotesis / pendiente — y no se colapsan.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

ORIGENES_VALIDOS = ("hecho", "hipotesis", "pendiente")

RUTAS_DESBLOQUEO = (
    "eliminar_necesidad",       # quitar la necesidad que origina el bloqueo
    "sustituir_mecanismo",      # otra forma de cumplir la misma función
    "desacoplar_dependencia",   # separar en tiempo/espacio/actores/componentes
)


@dataclass
class FichaBloqueo:
    """Ficha breve del bloqueo que guía la exploración guiada."""
    resultado_buscado: str                     # mejora observable
    bloqueo: str                               # qué impide mejorarlo
    explicacion_bloqueo: str                   # qué relación produce el impedimento
    origen_bloqueo: str = "hipotesis"          # hecho | hipotesis | pendiente
    solucion_referencia: str = ""              # cómo se resuelve hoy, si se conoce
    evidencia: list[dict[str, str]] = field(default_factory=list)  # {texto, origen, relacion}
    restricciones_obligatorias: list[str] = field(default_factory=list)
    supuestos_cuestionables: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "resultado_buscado": self.resultado_buscado,
            "bloqueo": self.bloqueo,
            "explicacion_bloqueo": self.explicacion_bloqueo,
            "origen_bloqueo": self.origen_bloqueo,
            "solucion_referencia": self.solucion_referencia,
            "evidencia": [dict(e) for e in self.evidencia],
            "restricciones_obligatorias": list(self.restricciones_obligatorias),
            "supuestos_cuestionables": list(self.supuestos_cuestionables),
        }


def validar_ficha(ficha: FichaBloqueo) -> list[str]:
    """Validación estructural honesta. Devuelve lista de errores (vacía = válida).

    Un campo no vacío es validación de estructura, no juicio de calidad
    (ASTRA §6). El origen declarado se comprueba contra el vocabulario.
    """
    errores: list[str] = []
    if not ficha.resultado_buscado.strip():
        errores.append("resultado_buscado vacío")
    if not ficha.bloqueo.strip():
        errores.append("bloqueo vacío")
    if not ficha.explicacion_bloqueo.strip():
        errores.append("explicacion_bloqueo vacía")
    if ficha.origen_bloqueo not in ORIGENES_VALIDOS:
        errores.append(f"origen_bloqueo '{ficha.origen_bloqueo}' no es {ORIGENES_VALIDOS}")
    for i, ev in enumerate(ficha.evidencia):
        if ev.get("origen") not in ORIGENES_VALIDOS:
            errores.append(f"evidencia[{i}].origen '{ev.get('origen')}' no es {ORIGENES_VALIDOS}")
        if ev.get("relacion") not in ("apoya", "contradice", "falta_comprobar"):
            errores.append(
                f"evidencia[{i}].relacion '{ev.get('relacion')}' debe ser "
                "apoya|contradice|falta_comprobar")
    return errores
