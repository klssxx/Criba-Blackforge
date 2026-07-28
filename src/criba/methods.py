"""Métodos de selección para CRIBA — catálogo expandido 6870 entradas.

Ejes morfológicos del catálogo completo:
  perspective  — 1700 lentes/puntos de vista
  generation   — 900 métodos de ideas disruptivas
  ruptura      — 1100 técnicas de ruptura de marco
  escape       — 1100 técnicas de salto fuera del espacio conocido
  methodology  — 2070 técnicas y metodologías externas

Estrategia de selección (Interesantedebate.txt):
  Cada activación recibe UNA entrada por eje (25% peso igual por eje base).
  Dentro de cada eje se elige primero familia, luego técnica concreta.
  El resto de slots se cubren con familias diversas no repetidas.
"""
from __future__ import annotations
import hashlib
import random
import re
from typing import Any

from .catalog import methods

# ---------------------------------------------------------------------------
# Ejes morfológicos canónicos (del debate + catálogo)
# ---------------------------------------------------------------------------
AXES = ["perspective", "generation", "ruptura", "escape", "methodology"]

# Palabras clave para sesgar ejes hacia la query
AXIS_KEYWORDS: dict[str, list[str]] = {
    "perspective": ["lente", "punto de vista", "perspectiva", "observar", "mirar",
                    "filosof", "psicolog", "cultura", "historia"],
    "generation":  ["idea", "innov", "disrupt", "crear", "generar", "nuevo",
                    "original", "inventar", "creatividad"],
    "ruptura":     ["romper", "ruptura", "cuestionar", "invalidar", "contradecir",
                    "supuesto", "marco", "paradigma", "desafiar"],
    "escape":      ["salir", "escape", "fuera", "espacio conocido", "límite",
                    "frontera", "desconocido", "saltar", "trasplante"],
    "methodology": ["método", "metodolog", "framework", "proceso", "técnica",
                    "kaizen", "lean", "agil", "six sigma", "dmaic"],
}

# Palabras clave para sesgar sector dentro de methodology
SECTOR_KEYWORDS: dict[str, list[str]] = {
    "seguridad":        ["seguridad", "ataque", "vulnerab", "pentest", "red team", "amenaza"],
    "innovacion":       ["innov", "startup", "lean", "agil", "design thinking", "sprint"],
    "investigacion":    ["investigaci", "hipótesis", "experimento", "muestra", "estudio"],
    "mejora_continua":  ["kaizen", "pdca", "dmaic", "six sigma", "lean", "mejora"],
    "tecnologia":       ["software", "algoritmo", "sistema", "arquitectura", "código"],
    "negocio":          ["negocio", "mercado", "cliente", "ventas", "estrategia"],
}


def _detect_axes(query: str) -> list[str]:
    """Detecta qué ejes son más relevantes para la query (sin excluir los demás)."""
    q = query.casefold()
    scored = []
    for axis, keywords in AXIS_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in q)
        scored.append((score, axis))
    scored.sort(reverse=True)
    # Devuelve todos los ejes ordenados por relevancia
    return [ax for _, ax in scored]


def _detect_sectors(query: str) -> list[str]:
    """Detecta sectores relevantes para el eje methodology."""
    q = query.casefold()
    found = []
    for sector, keywords in SECTOR_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            found.append(sector)
    return found


def select_methods(
    count: int = 8,
    mode: str = "balanced",
    manual: list[str] | None = None,
    query: str | None = None,
    granularity_filter: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Selecciona métodos cubriendo los 5 ejes morfológicos del catálogo expandido.

    Con count >= 5 garantiza al menos 1 entrada por eje (perspective, generation,
    ruptura, escape, methodology).  Slots restantes se rellenan con familias distintas
    maximizando diversidad.

    Seed determinista por query: misma query → mismo paquete (reproducible).
    """
    if not 1 <= count <= 20:
        raise ValueError("supporting_methods debe estar entre 1 y 20.")

    seed = int(hashlib.md5((query or "").encode()).hexdigest()[:8], 16) if query else 42
    rng = random.Random(seed)

    available = methods()
    if granularity_filter:
        available = [m for m in available if m.get("granularity", "micro_technique") in granularity_filter]

    if not available:
        return []

    # Agrupar por eje (campo 'axis' introducido en el catálogo expandido;
    # fallback a family para entradas del catálogo legacy)
    by_axis: dict[str, list[dict[str, Any]]] = {ax: [] for ax in AXES}
    for m in available:
        ax = m.get("axis") or ""
        if ax in by_axis:
            by_axis[ax].append(m)
        else:
            # entradas legacy sin campo axis: asignarlas por familia
            fam = m.get("family", "")
            if "lente" in fam or "perspectiva" in fam or fam in (
                "ciencia_realidad", "filosofia", "psicologia", "historia_culturas",
                "lente_avanzado", "decision_riesgo",
            ):
                by_axis["perspective"].append(m)
            elif fam in ("ruptura_marco",):
                by_axis["ruptura"].append(m)
            elif fam in ("salto_espacio",):
                by_axis["escape"].append(m)
            elif fam in ("general", "innovacion", "inversion"):
                by_axis["generation"].append(m)
            else:
                by_axis["methodology"].append(m)

    # Ordenar ejes por relevancia para la query
    axes_ordered = _detect_axes(query or "")
    detected_sectors = _detect_sectors(query or "")

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    used_families: set[str] = set()

    def pick_from_axis(ax: str) -> dict[str, Any] | None:
        pool = [m for m in by_axis[ax] if m["id"] not in selected_ids]
        if not pool:
            return None
        # Para methodology: priorizar sector relevante
        if ax == "methodology" and detected_sectors:
            sector_pool = [m for m in pool if m.get("sector", "") in detected_sectors]
            if sector_pool:
                pool = sector_pool
        # Para todos: preferir familia no usada aún
        diverse = [m for m in pool if m.get("family", "") not in used_families]
        if diverse:
            pool = diverse
        return rng.choice(pool)

    # Primer pase: 1 por eje en orden de relevancia
    for ax in axes_ordered:
        if len(selected) >= count:
            break
        m = pick_from_axis(ax)
        if m:
            selected.append({**m, "reason": m.get("selection_reason", "")})
            selected_ids.add(m["id"])
            used_families.add(m.get("family", ""))

    # Segundo pase: rellenar con diversidad máxima (familia no repetida)
    if len(selected) < count:
        all_remaining = [m for m in available if m["id"] not in selected_ids]
        rng.shuffle(all_remaining)
        for m in all_remaining:
            if len(selected) >= count:
                break
            if m.get("family", "") not in used_families:
                selected.append({**m, "reason": m.get("selection_reason", "")})
                selected_ids.add(m["id"])
                used_families.add(m.get("family", ""))

    # Tercer pase: completar sin restricción de familia si aún faltan slots
    if len(selected) < count:
        all_remaining = [m for m in available if m["id"] not in selected_ids]
        rng.shuffle(all_remaining)
        for m in all_remaining:
            if len(selected) >= count:
                break
            selected.append({**m, "reason": m.get("selection_reason", "")})
            selected_ids.add(m["id"])

    return selected[:count]
