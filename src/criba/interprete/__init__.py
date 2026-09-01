"""Interprete-serendipia: pipeline de interpretación epistemológica.

- PreFilter: prefiltrado causal top-N (Dh 0.45-0.85 + SOTA taboo + novelty band).
- Protocolo: 11 preguntas de expansión epistemológica (serendipia).
- CloudInterprete: envía al modelo z.ai (glm-5.3-flash) con fallback local.
- InterpreteStore: registro SQLite auditable, deduplicación por seed+comb_id.

Integración en engine.activate() como capa aditiva: el packet CRIBA base queda
intacto; el interprete añade el bloque innovation.interprete.
"""
