# ADR P10-T09 — Motor de veredicto conservador de prior art

**Estado:** `VERIFIED` localmente para P10-T09; P10 no está cerrada.  
**Fecha:** 2026-09-05

## Contexto

El pipeline canónico exige:

```text
CROSS-DOMAIN SCOUT -> SKEPTIC -> VERDICT
```

El blueprint permite solamente `KNOWN`, `NEAR_PRIOR_ART`,
`PARTIAL_PRIOR_ART`, `UNRESOLVED` y `SURVIVED_SEARCH`; prohíbe
`PROVEN_NEW` por simple ausencia. P10-T08 produce cobertura/procedencia,
no comparación semántica o materialidad.

`PriorArtMatch` aporta documento, tipo y similitud, pero no contiene un
contrato que demuestre materialidad. No existe un umbral canónico para pasar
de un match a `KNOWN` o `NEAR_PRIOR_ART`.

## Decisión

Se añade `PriorArtVerdictEngine.assess(...) -> PriorArtAssessment`, puro y
determinista. Consume:

- `InventionCandidate`;
- `Mapping[str, SourceQueryResult]` de T07;
- `PriorArtSkepticReport` de T08 para el mismo candidato;
- `Sequence[PriorArtMatch]` ya normalizados.

Las únicas salidas automatizadas de este contrato son:

1. `UNRESOLVED` si hay fallo de fuente, fuente vacía, procedencia ausente o
   cualquier gap del Skeptic. La cobertura se reconstruye desde los resultados;
   un payload T08 manipulado no puede ocultarla.
2. `PARTIAL_PRIOR_ART` si no hay limitaciones y existe al menos un
   `PriorArtMatch` normalizado. No se usa `similarity` como umbral.
3. `SURVIVED_SEARCH` sólo si no hay limitaciones ni matches.

`KNOWN` y `NEAR_PRIOR_ART` no se infieren automáticamente: exigen un futuro
contrato explícito de materialidad. `PROVEN_NEW` no aparece en la API,
enum, motor ni pruebas de salida.

## Invariantes

- Sin red, proveedor, credencial, persistencia o mutación de los inputs.
- Los resultados y matches se ordenan establemente; los queries se deduplican
  en orden de `source_id`.
- El motor devuelve el `PriorArtAssessment` ya definido en L1.
- `CrossDomainScout.validate_downstream_handoff` recibe el informe T08 real y
  el veredicto final real en la prueba de integración.
- Match malformado se rechaza con `TypeError`, no con `AttributeError` interno.

## Evidencia

- RED observado para API ausente, fuente vacía encubierta, export público
  ausente, match no clasificado, orden no determinista, match malformado,
  match que tapaba un gap y procedencia encubierta.
- GREEN final: 8 tests P10-T09; 45 tests P10/contratos/boundaries;
  regresión CRIBA `948 passed, 1 warning`.
- Ruff, mypy y compileall verdes; `COST=0` sin red externa.

## Consecuencias y límite

El resultado `SURVIVED_SEARCH` significa sólo supervivencia a la búsqueda
acotada. No afirma novedad, patentabilidad, originalidad ni ausencia mundial de
prior art. P10-T10 debe usar estas salidas para mutation/re-search; P10-T12 debe
intentar refutar la cadena completa.

## Rollback

El write-set específico de T09 es `prior_art/verdict.py`,
`test_prior_art_verdict_engine.py`, este ADR y su journal. La única línea de
export en `prior_art/__init__.py` se revierte de forma lineal revisada porque ese
archivo también contiene cambios preexistentes de T07/T08. No usar reset/clean
en el árbol compartido.
