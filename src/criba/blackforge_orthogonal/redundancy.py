"""Antirredundancia en 4 niveles.

Detecta si una idea nueva es redundante con el historial existente.
Niveles (de más superficial a más profundo):

1. TEXTUAL      — Mismo texto (Jaccard sobre tokens)
2. SEMANTICO    — Misma propuesta esencial (estructura + mecanismo)
3. ESTRUCTURAL  — Misma OrthogonalSignature (mismos ejes/valores)
4. CAUSAL       — Mismo mecanismo subyacente (causalidad + epistemología)

Decisiones:
    NEW             — Idea estructuralmente distinta
    VARIANT         — Mismo mecanismo causal, distinta forma
    DERIVATIVE      — Misma estructura, distinto texto
    MERGE_CANDIDATE — Alta similitud semántica
    REDUNDANT       — Texto prácticamente idéntico
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .signature import OrthogonalSignature


class RedundancyLevel(Enum):
    TEXTUAL = "TEXTUAL"
    SEMANTIC = "SEMANTIC"
    STRUCTURAL = "STRUCTURAL"
    CAUSAL = "CAUSAL"


class RedundancyDecision(Enum):
    NEW = "NEW"
    VARIANT = "VARIANT"
    DERIVATIVE = "DERIVATIVE"
    MERGE_CANDIDATE = "MERGE_CANDIDATE"
    REDUNDANT = "REDUNDANT"


@dataclass
class RedundancyResult:
    """Resultado de la verificación de redundancia."""
    level: RedundancyLevel
    similarity: float
    decision: RedundancyDecision
    explanation: str


class RedundancyChecker:
    """Verifica redundancia en 4 niveles.

    Uso:
        checker = RedundancyChecker()
        result = checker.check(new_idea, existing_idea)
    Umbrales por defecto:
        textual > 0.95     → REDUNDANT
        semántico > 0.85   → MERGE_CANDIDATE
        estructural > 0.90 → DERIVATIVE
        causal > 0.95      → VARIANT
    """

    def __init__(
        self,
        textual_threshold: float = 0.95,
        semantic_threshold: float = 0.85,
        structural_threshold: float = 0.90,
        causal_threshold: float = 0.95,
    ):
        self.textual_threshold = textual_threshold
        self.semantic_threshold = semantic_threshold
        self.structural_threshold = structural_threshold
        self.causal_threshold = causal_threshold

    def check(
        self,
        new_signature: OrthogonalSignature,
        existing_signature: OrthogonalSignature,
        new_text: str = "",
        existing_text: str = "",
    ) -> RedundancyResult:
        """Verifica redundancia entre dos ideas.

        Args:
            new_signature: Firma ortogonal de la idea nueva
            existing_signature: Firma ortogonal de la idea existente
            new_text: Texto descriptivo de la idea nueva (para nivel textual)
            existing_text: Texto descriptivo de la idea existente
        """
        # Nivel 1: TEXTUAL
        textual_sim = self._textual_similarity(new_text, existing_text)
        if textual_sim > self.textual_threshold:
            return RedundancyResult(
                level=RedundancyLevel.TEXTUAL,
                similarity=textual_sim,
                decision=RedundancyDecision.REDUNDANT,
                explanation="Textos prácticamente idénticos"
            )

        # Nivel 2: SEMANTICO (combinación de textual + estructural)
        # Va ANTES que estructural para detectar "misma estructura, distinto texto"
        semantic_sim = self._semantic_similarity(
            new_signature, existing_signature, new_text, existing_text
        )
        if semantic_sim > self.semantic_threshold:
            return RedundancyResult(
                level=RedundancyLevel.SEMANTIC,
                similarity=semantic_sim,
                decision=RedundancyDecision.MERGE_CANDIDATE,
                explanation="Describen esencialmente la misma propuesta"
            )

        # Nivel 3: ESTRUCTURAL
        structural_sim = new_signature.similarity(existing_signature)
        if structural_sim > self.structural_threshold:
            return RedundancyResult(
                level=RedundancyLevel.STRUCTURAL,
                similarity=structural_sim,
                decision=RedundancyDecision.DERIVATIVE,
                explanation="Misma OrthogonalSignature (variantes estructurales)"
            )

        # Nivel 4: CAUSAL
        causal_sim = self._causal_similarity(new_signature, existing_signature)
        if causal_sim > self.causal_threshold:
            return RedundancyResult(
                level=RedundancyLevel.CAUSAL,
                similarity=causal_sim,
                decision=RedundancyDecision.VARIANT,
                explanation="Obtienen el beneficio mediante el mismo mecanismo"
            )

        # No hay redundancia significativa
        return RedundancyResult(
            level=RedundancyLevel.TEXTUAL,
            similarity=max(textual_sim, semantic_sim, structural_sim, causal_sim),
            decision=RedundancyDecision.NEW,
            explanation="Idea estructuralmente distinta"
        )

    def _textual_similarity(self, text_a: str, text_b: str) -> float:
        """Jaccard sobre tokens de texto."""
        if not text_a or not text_b:
            return 0.0
        tokens_a = set(text_a.lower().split())
        tokens_b = set(text_b.lower().split())

        if not tokens_a and not tokens_b:
            return 1.0
        if not tokens_a or not tokens_b:
            return 0.0

        intersection = len(tokens_a & tokens_b)
        union = len(tokens_a | tokens_b)
        return intersection / union if union > 0 else 0.0

    def _semantic_similarity(
        self,
        sig_a: OrthogonalSignature,
        sig_b: OrthogonalSignature,
        text_a: str = "",
        text_b: str = "",
    ) -> float:
        """Similitud semántica: combinación de textual + estructural.

        Si la estructura es idéntica pero el texto tiene algún solape,
        es un MERGE_CANDIDATE (misma propuesta, distinta redacción).
        Si el texto es completamente distinto, pasa a ESTRUCTURAL (DERIVATIVE).
        """
        textual_sim = self._textual_similarity(text_a, text_b)
        structural_sim = sig_a.similarity(sig_b)

        # Si la estructura es idéntica pero texto con solape → MERGE_CANDIDATE
        if structural_sim == 1.0 and textual_sim > 0.0 and textual_sim < self.textual_threshold:
            return 0.9  # Fuerza MERGE_CANDIDATE

        # Peso: 40% textual, 60% estructural
        return 0.4 * textual_sim + 0.6 * structural_sim

    def _causal_similarity(
        self,
        sig_a: OrthogonalSignature,
        sig_b: OrthogonalSignature,
    ) -> float:
        """Similitud causal: compara ejes de CAUSALIDAD, EPISTEMOLOGIA y TRANSFORMACION."""
        causal_axes = ["AX-01", "AX-07", "AX-11"]

        matches = 0
        total = 0

        for axis_id in causal_axes:
            vals_a = set(sig_a.values_for_axis(axis_id))
            vals_b = set(sig_b.values_for_axis(axis_id))

            if vals_a or vals_b:
                total += 1
                if vals_a & vals_b:
                    matches += 1

        return matches / total if total > 0 else 0.0
