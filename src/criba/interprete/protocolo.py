"""Protocolo de Preguntas de Expansión Epistemológica (Serendipia).

Antes de que un modelo interprete las candidatas, CRIBA les aplica un
protocolo de exposición estructurada que convierte \"azar combinatorio\" en
\"serendipia instrumental\": el modelo no juzga una idea, sino que la
interroga a través de 11 ejes documentados (anomalía observables, conexión
no obvia a otro dominio, contraintuitividad, etc.).

Las preguntas están extraídas del reporte epistemológico del ecosistema
(CONTEXTO_TECNICO_CRIBA_BLACKFORGE.md §serendipia). Cada una lleva un
``trigger`` léxico opcional: si la idea ya contiene ese término, la pregunta
se marca como ``auto_cubierta`` (no se repite).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PreguntaExpansion:
    id: str
    eje: str
    pregunta: str
    trigger: str = ""
    auto_cubrir: tuple[str, ...] = ()


PREGUNTAS: tuple[PreguntaExpansion, ...] = (
    PreguntaExpansion(
        id="Q1", eje="anomalia_observable",
        pregunta="¿Qué anomalía o patrón observado CONTRADICTA el comportamiento esperado del sistema actual?",
        trigger="anomal",
        auto_cubrir=("falla", "anomal", "patrón inesperado", "comportamiento inesperado"),
    ),
    PreguntaExpansion(
        id="Q2", eje="novedad_front",
        pregunta="¿En qué punto la idea rompe con el estado del arte identificado como dominante para este problema?",
        trigger="estado del arte",
    ),
    PreguntaExpansion(
        id="Q3", eje="conexion_no_obvia",
        pregunta="¿Qué conexión causal NO OBVIA existe entre esta idea y un mecanismo de otro dominio?",
        trigger="dominio",
        auto_cubrir=("otro dominio", "dominio opuesto", "biomimética", "análogo a"),
    ),
    PreguntaExpansion(
        id="Q4", eje="contraintuitividad",
        pregunta="¿Qué aspecto de la idea es CONTRAINTUITIVO para un experto en el campo?",
        trigger="intuitiv",
    ),
    PreguntaExpansion(
        id="Q5", eje="factibilidad_implicita",
        pregunta="¿Qué implica de factibilidad/falsabilidad la idea según el marco de contención (S1/S2/S3) asignado por el gobierno causal?",
        trigger="factibilidad",
    ),
    PreguntaExpansion(
        id="Q6", eje="implicaciones_no_deseadas",
        pregunta="¿Qué implicación SISTÉMICA no deseada podría surgir al aplicar esta idea a escala?",
        trigger="implicacion",
    ),
    PreguntaExpansion(
        id="Q7", eje="beneficios_opositos",
        pregunta="¿Quién se beneficia y quién se OPONE a esta idea y por qué?",
        trigger="beneficiar",
    ),
    PreguntaExpansion(
        id="Q8", eje="falsacion_minima",
        pregunta="¿Qué experimento MÍNIMO haría falsar esta idea, y qué haría la hipótesis nula (H0) respecto al axioma rompido?",
        trigger="falsificacion",
    ),
    PreguntaExpansion(
        id="Q9", eje="epifenomeno",
        pregunta="¿Qué epifenómeno o efecto colateral podrïrse interpretar como el VERDADERO motor de cambio?",
        trigger="epifenomeno",
    ),
    PreguntaExpansion(
        id="Q10", eje="inversa",
        pregunta="¿Cómo cambia la idea si se INVIERTE el rol de cada actor implicado?",
        trigger="actor",
    ),
    PreguntaExpansion(
        id="Q11", eje="temporal",
        pregunta="¿Qué sucede si esta idea se aplica en contextos temporales Opuestos (pasado vs futuro)?",
        trigger="temporal",
    ),
)

# Mapeo eje -> pregunta (para acceso rápido)
POR_EJE: dict[str, PreguntaExpansion] = {p.eje: p for p in PREGUNTAS}


def protocolo_para(idea: dict[str, Any]) -> dict[str, Any]:
    """Construye el bloque de protocolo para una idea: texto completo + ejes
    auto-cubiertos marcados. Usado como contexto para el modelo interprete."""
    texto_idea = f"{idea.get('description', '')} {idea.get('mechanism_causal', '')}".lower()
    items = []
    auto = []
    for p in PREGUNTAS:
        covered = any(t in texto_idea for t in p.auto_cubrir) or (p.trigger and p.trigger in texto_idea)
        if covered:
            auto.append(p.id)
        items.append({
            "id": p.id,
            "eje": p.eje,
            "pregunta": p.pregunta,
            "auto_cubierta": covered,
        })
    return {
        "preguntas": items,
        "auto_cubiertas": auto,
        "count": len(items),
        "count_auto": len(auto),
        "count_pending": len(items) - len(auto),
    }
