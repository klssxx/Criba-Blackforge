# ADR P10-T08 — Skeptic determinista de evidencia de prior art

**Estado:** `VERIFIED` para P10-T08; P10 y P10-T07 no están cerrados.  
**Fecha:** 2026-09-05  
**Alcance:** `PriorArtSkeptic` de P10-T08 únicamente.

## Fuentes de autoridad

- `docs/architecture/CRIBA_BLUEPRINT_ULTIMATE.txt`, §25–26 y P10-T08.
- `spec/CRIBA_BLACKFORGE_MASTER_SPEC.md`, §§8.4, 8.6 y 8.7.
- `docs/architecture/adr/ADR-P10-T07-cross-domain-contract.md`.
- `src/criba/intelligence/contracts.py` y `src/criba/intelligence/enums.py`.

El blueprint coloca el orden obligatorio en:

```text
cross-domain evidence -> SKEPTIC -> VERDICT
```

P10-T09 sigue siendo el propietario del veredicto de prior art. P10-T08 no lo
anticipa ni lo sustituye.

## Decisión

Se añade un componente puro y determinista:

```python
PriorArtSkeptic().review(
    candidate: InventionCandidate,
    results: Mapping[str, SourceQueryResult],
) -> PriorArtSkepticReport
```

`PriorArtSkepticReport` es JSON-safe y también implementa `Mapping[str, object]`
para poder pasar directamente al guard fail-closed de P10-T07 sin un adaptador
paralelo. Expone el contrato de pasada adversarial de la especificación:

- tesis bajo ataque;
- supuestos, desafíos causales/fácticos y explicaciones alternativas;
- gaps de evidencia;
- pruebas de falsación y criterios de descarte;
- partes supervivientes y estado de proceso.

## Semántica limitada

El componente evalúa la **integridad y cobertura mínima de evidencia**, no el
solapamiento semántico entre mecanismo y documento.

Para cada resultado, en orden estable por `source_id`:

1. `ok=False` produce `source_failure:<source_id>` sin copiar `error`.
2. Una respuesta válida sin documentos produce `empty_source:<source_id>`.
3. Un documento sin `ProvenanceRecord` produce
   `missing_provenance:<source_id>:<doc_id>`.
4. Cada documento normalizado genera una prueba explícita
   `compare_candidate_mechanism:<source_id>:<doc_id>` para P10-T09.

El estado del Skeptic es deliberadamente **no final**:

- `requires_experiment` cuando existe cualquier gap;
- `survives_with_conditions` cuando la cobertura formal está completa.

Estos valores expresan el resultado de la microfase adversarial. No pertenecen a
`PriorArtVerdict`, no implican `SURVIVED_SEARCH`, no emiten
`PriorArtAssessment` y nunca pueden producir `PROVEN_NEW`.

## Invariantes

- No hay I/O, red, proveedor, credencial, flag ni import de CRIBA legacy/SUPRA.
- El candidato y los resultados fallan rápido si su contrato estructural es
  inválido; documentos no `EvidenceDocument` se rechazan fail-closed.
- El informe no muta entrada ni expone texto de errores externos.
- El orden de un mapping de entrada no altera el payload de salida.
- P10-T07 puede validar el handoff real con el informe y un valor permitido de
  `PriorArtVerdict`, pero la decisión final pertenece a P10-T09.

## Fuera de alcance

- Similaridad léxica, semántica, embeddings o LLM.
- Clasificar documentos como prior art material.
- Emitir `KNOWN`, `NEAR_PRIOR_ART`, `PARTIAL_PRIOR_ART`, `UNRESOLVED` o
  `SURVIVED_SEARCH`.
- Declarar novedad, originalidad, patentabilidad o freedom-to-operate.
- Cambiar T07, T09, T10, sources, transports o flags IIE.

## Evidencia

Las pruebas usan `Transport` inyectado; no hubo llamadas de red ni coste.

- RED: módulo inexistente, export público inexistente, documento malformado y
  procedencia ausente produjeron los fallos esperados antes de cada cambio.
- GREEN: `tests/intelligence/test_prior_art_skeptic.py` → `6 passed`.
- Integración P10: skeptic + CrossDomainScout + protocolos/contratos/boundaries
  → `37 passed`.
- Regresión CRIBA del snapshot final de código → `940 passed, 1 warning`.

## Limitaciones y siguiente contrato

Un informe con cobertura formal completa conserva `survives_with_conditions`, no
un veredicto de búsqueda. P10-T09 debe consumir el informe junto con los
resultados de fuente y decidir explícitamente entre los valores existentes de
`PriorArtVerdict`. P10-T07 permanece `PARTIAL` hasta ese handoff completo.
