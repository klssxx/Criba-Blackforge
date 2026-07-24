# DEBT AND PLACEHOLDER AUDIT — CRIBA + BLACKFORGE

Fecha: 2026-07-24 | FASE 2 (TODO/FIXME scan)
Búsqueda: `TODO|FIXME|XXX|HACK|BUG|NotImplementedError|not_implemented|pass|placeholder|stub|mock temporal|fake|demo-only` sobre `src/criba`.

## Resultado

| Marcador | Coincidencias reales | Veredicto |
|----------|---------------------|-----------|
| `TODO`/`FIXME`/`XXX`/`HACK` (comentario) | 0 | ✅ ninguna |
| `raise NotImplementedError` | 1 (`agentic.py:101`) | ⚠️ by-design |
| `not_implemented` en texto/dicts | 2 (`agentic.py`, `engine_v1_audit_intent.py`) | ✅ inócuos |
| `pass` como placeholder | 0 reales | ✅ |
| `placeholder`/`stub`/`mock`/`fake`/`demo-only` | 0 | ✅ |

## Hallazgo único (no corregir sin orden)

- **`src/criba/agentic.py:100-105`** — `get_layer("AGENTIC", ...)` lanza
  `NotImplementedError`. Es **intencional**: el módulo documenta que `LOCAL_MVP`
  es el único adapter activo hoy; `AGENTIC` (multi-agent + RAG + evaluador externo)
  es un "future hook" del roadmap. `LocalAgenticLayer.evaluate_novelty` (líneas
  86-93) retorna `{"status": "not_implemented_yet"}` deliberadamente — la novedad
  se mide dentro del engine por divergencia de ejes causales + CCA, no por
  evaluador externo.
- **Impacto**: ninguno en funcionamiento (204 passed). CLI/API/MCP usan `activate()`
  directo, no pasan por `get_layer("AGENTIC")`. No es defecto, es frontera futura.

## Conclusión

El motor está **limpio de deuda de marcadores**. No hay TODO/FIXME pendientes que
corregir. El único `NotImplementedError` es una frontera documentada y fuera del
release. No se implementa AGENTIC (no solicitado, fuera de alcance).

## Acción

NINGUNA modificación de código por esta fase. Se documenta y se excluye del release.
