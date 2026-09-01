"""Interpreta salidas del motor CRIBA (offline, determinista).

El motor devuelve combinaciones de técnicas con scores numéricos.
Este módulo las traduce a frases legibles en ES o EN sin llamadas a LLM.
"""
from __future__ import annotations

import re
from typing import Any

# Plantillas ES / EN  --------------------------------------------------------
_TEMPLATES_ES = [
    "Combina {m1} con {m2} para abordar el dominio «{domain}».",
    "Aplica la técnica «{m1}» junto con «{m2}» orientada a {domain}.",
    "Fusiona «{m1}» y «{m2}» para generar una solución en {domain}.",
    "Integra el enfoque de {m1} con el mecanismo de {m2} en {domain}.",
    "Usa {m1} como palanca y {m2} como refuerzo para innovar en {domain}.",
]
_TEMPLATES_EN = [
    "Combine {m1} with {m2} to address the «{domain}» domain.",
    "Apply technique «{m1}» together with «{m2}» targeting {domain}.",
    "Fuse «{m1}» and «{m2}» to generate a solution in {domain}.",
    "Integrate the {m1} approach with the {m2} mechanism in {domain}.",
    "Use {m1} as leverage and {m2} as amplifier to innovate in {domain}.",
]

_QUALITY_LABEL_ES = {
    "critical": "Crítica", "essential": "Alta", "core": "Alta",
    "high": "Alta", "medium": "Media", "low": "Baja",
    "": "Media",
}
_QUALITY_LABEL_EN = {
    "critical": "Critical", "essential": "High", "core": "High",
    "high": "High", "medium": "Medium", "low": "Low",
    "": "Medium",
}
_NOVELTY_LABEL_ES = ["Baja", "Media", "Alta", "Muy alta"]
_NOVELTY_LABEL_EN = ["Low", "Medium", "High", "Very high"]

_FAMILY_ES: dict[str, str] = {
    "cross_domain_transfer": "transferencia entre dominios",
    "human_legal_ethics": "ética y legalidad",
    "experimentation_benchmarks": "experimentación y benchmarks",
    "red_team": "red team",
    "exploitation": "explotación",
    "defense": "defensa",
    "social_engineering": "ingeniería social",
    "ai_ml": "IA y ML",
    "forensic": "forense",
    "research": "investigación",
}
_FAMILY_EN: dict[str, str] = {
    "cross_domain_transfer": "cross-domain transfer",
    "human_legal_ethics": "ethics and legality",
    "experimentation_benchmarks": "experimentation and benchmarking",
    "red_team": "red team",
    "exploitation": "exploitation",
    "defense": "defense",
    "social_engineering": "social engineering",
    "ai_ml": "AI and ML",
    "forensic": "forensics",
    "research": "research",
}


def _clean(s: str) -> str:
    """Elimina prefijos de ID tipo BF-CYB-R1000-0888 y símbolos sobrantes."""
    s = re.sub(r"^[A-Z]{1,5}-[A-Z]{2,6}-[A-Z0-9]+-\d+\s*", "", s or "")
    return s.strip(" →×·—") or s


def _novelty_idx(score: float) -> int:
    if score >= 0.85:
        return 3
    if score >= 0.65:
        return 2
    if score >= 0.35:
        return 1
    return 0


def format_idea(idea: dict[str, Any], lang: str = "es", idx: int = 0) -> dict[str, str]:
    """Devuelve title / description / novelty / quality / sentence legibles."""
    es = lang == "es"
    templates = _TEMPLATES_ES if es else _TEMPLATES_EN
    fam_map = _FAMILY_ES if es else _FAMILY_EN
    nov_labels = _NOVELTY_LABEL_ES if es else _NOVELTY_LABEL_EN
    qual_map = _QUALITY_LABEL_ES if es else _QUALITY_LABEL_EN

    m1_raw = _clean(idea.get("method1") or idea.get("title") or "Método A")
    m2_raw = _clean(idea.get("method2") or "Método B")
    fam1 = idea.get("family1") or idea.get("family") or ""
    fam2 = idea.get("family2") or ""
    domain = fam_map.get(fam1) or fam_map.get(fam2) or fam1 or "el dominio objetivo"

    # Si el motor ya produce un título legible (sin prefijo ID), úsalo
    raw_title = (idea.get("title") or "").strip()
    id_pattern = re.compile(r"^[A-Z]{1,5}-[A-Z]{2,6}-[A-Z0-9]+-\d+")
    has_id = id_pattern.match(raw_title)

    if has_id or not raw_title or "×" in raw_title:
        # Genera título limpio desde métodos
        m1_short = m1_raw[:40] if m1_raw else "Método A"
        m2_short = m2_raw[:40] if m2_raw else "Método B"
        title = f"{m1_short} × {m2_short}"
    else:
        title = raw_title[:80]

    # A validated language layer already understands the user's problem; do
    # not overwrite its semantic description with the old mechanical template.
    semantic_description = str(idea.get("description") or "").strip()
    if idea.get("semantic_source") == "local_model" and semantic_description:
        sentence = semantic_description
    else:
        tpl = templates[idx % len(templates)]
        sentence = tpl.format(
            m1=m1_raw[:50] or "Método A",
            m2=m2_raw[:50] or "Método B",
            domain=domain,
        )

    conv = idea.get("convergence") or {}
    novelty_raw = float(conv.get("novelty") or idea.get("score") or 0)
    quality_raw = (idea.get("quality") or "").lower()
    for k in _QUALITY_LABEL_ES:
        if k and k in quality_raw:
            quality_raw = k
            break

    return {
        "title": title,
        "sentence": sentence,
        "novelty": nov_labels[_novelty_idx(novelty_raw)],
        "quality": qual_map.get(quality_raw, qual_map[""]),
        "novelty_raw": novelty_raw,
    }
