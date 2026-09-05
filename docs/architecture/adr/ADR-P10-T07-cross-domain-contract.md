# ADR P10-T07 — Contrato de evidencia cross-domain

**Estado:** `PARTIAL / HIGH_REVIEW`
**Fecha:** 2026-09-04
**Alcance:** `CrossDomainScout` de P10-T07 únicamente.

## 1. Fuentes de autoridad

Este contrato se deriva de:

- `docs/architecture/CRIBA_BLUEPRINT_ULTIMATE.txt`, §§6, 7, 12, 25, 26, 34 y 62.
- `spec/CRIBA_BLACKFORGE_MASTER_SPEC.md`, §§1.4, 8.2–8.7 y 10.1–10.10.
- `src/criba/intelligence/contracts.py`: `QueryVariant`, `SourceQueryResult`,
  `EvidenceDocument`, `PriorArtAssessment`.
- `src/criba/intelligence/sources/protocol.py`: `IntelligenceSource` y
  `SourceContext`.
- `src/criba/intelligence/sources/transport.py`: `TransportBudget`,
  `BudgetExceeded`.
- `src/criba/intelligence/invention/cross_domain.py`: T055, que exige
  conceptos explícitos compartidos entre dominios explícitos para proponer una
  transferencia.

El blueprint nombra `skeptic.py` y `verdict.py` como P10-T08 y P10-T09. No
existen todavía como consumidores implementados en este árbol. Por tanto, este
ADR define el límite de handoff de T07, no implementa T08/T09.

## 2. Decisión semántica

`CrossDomainScout` **no demuestra ni calcula una analogía**. Su responsabilidad
es recopilar evidencia de búsqueda agrupada por fuentes de dominios distintos,
para que un consumidor posterior pueda evaluar una analogía.

Una analogía cross-domain válida requiere, como mínimo, una relación explícita
entre elementos de dos dominios y un mecanismo o concepto transferible. La
similitud léxica del query, la presencia de resultados en dos APIs, la rareza o
la ausencia de resultados no bastan. La transferencia T055 existente sigue
siendo la referencia para conceptos y dominios explícitos.

En consecuencia, T07 no produce `PriorArtAssessment`, `PriorArtMatch`,
`similarity`, `KNOWN`, `SURVIVED_SEARCH` ni `PROVEN_NEW`.

## 3. Entrada válida

La API observable es:

```python
CrossDomainScout(
    sources: Sequence[IntelligenceSource],
    *,
    budget: TransportBudget | None = None,
).cross_search(
    variant: QueryVariant,
    *,
    limit_per_source: int = 5,
) -> dict[str, SourceQueryResult]
```

### 3.1 Fuentes

Cada fuente debe:

1. implementar `source_id()` y devolver un `str` no vacío, sin espacios
   laterales;
2. declarar `KIND` como `str` no vacío, sin espacios laterales;
3. exponer `context.transport` con `get(...)` y un objeto `budget` compatible
   con `TransportBudget`;
4. tener un `source_id` único dentro de la instancia del scout.

Los IDs se comparan literalmente después de validar que no tienen espacios
laterales. No se corrigen ni normalizan silenciosamente.

El dominio para la prueba cross-domain es `KIND.strip().casefold()`. No se
hace inferencia ontológica ni se transforma singular/plural. Esto deja visible
una ambigüedad existente: algunos adapters declaran, por ejemplo, `patent` y
otros `patents`; el catálogo debe unificarlos en una tarea de fuentes separada,
no T07.

Debe haber al menos dos dominios `KIND` distintos. Dos fuentes distintas del
mismo dominio no constituyen una analogía cross-domain y se rechazan.

### 3.2 Query

`variant` debe ser una instancia de `QueryVariant` y `variant.text` debe ser un
`str` no vacío después de `strip()`. El texto original se conserva literalmente
en cada `SourceQueryResult.query_text`; no se reescribe el query para simular
una relación semántica.

`language`, `origin` y `technique_ids` se conservan en el `QueryVariant`, pero
T07 no los interpreta como prueba de analogía.

### 3.3 Límites

`limit_per_source` debe ser un entero real, no `bool`, y mayor o igual que 1.

`budget`, si se proporciona, debe ser un `TransportBudget` con
`max_requests >= 1`, `0 <= requests_made <= max_requests` y `max_runtime_s > 0` finito. Si no se proporciona, T07 crea
un presupuesto de ejecución único con los valores por defecto de
`TransportBudget`.

## 4. Salida esperada

`cross_search` devuelve un `dict` con:

- exactamente una entrada por `source_id` válido;
- claves insertadas en orden lexicográfico estable por `source_id`,
  independiente del orden de `sources` recibido;
- un `SourceQueryResult` por fuente;
- `result.source_id == key` y `result.query_text == variant.text`;
- documentos normalizados por el adapter, sin reinterpretarlos como analogías;
- `ok=True` para una respuesta válida, aunque esté vacía;
- `ok=False` y un error controlado para una excepción, un fallo de presupuesto o
  un contrato de adapter inválido.

Una fuente vacía (`ok=True`, `documents=[]`) no equivale a una fuente caída.
T07 no fusiona, puntúa ni deduplica documentos entre fuentes: la deduplicación
semántica y la representación de una analogía son responsabilidades posteriores.

## 5. Invariantes

1. No hay `source_id` duplicados.
2. No se acepta una colección con menos de dos dominios `KIND` distintos.
3. El texto de consulta se conserva sin modificación.
4. El orden de las claves no depende de la concurrencia ni del orden de entrada.
5. Todos los `source_id` aparecen una sola vez, también cuando una fuente falla.
6. El presupuesto de requests es global para la llamada: todos los transports
   usan el mismo `TransportBudget`; no se reinicia por fuente ni por dominio. El
   budget pertenece a la instancia del scout y tampoco se reinicia al repetir
   `cross_search`; una ejecución nueva debe crear un budget nuevo.
7. `budget.requests_made <= budget.max_requests` siempre.
8. Una fuente fallida no borra ni invalida silenciosamente resultados válidos de
   otras fuentes.
9. T07 no eleva un veredicto de prior art ni convierte ausencia de resultados
   en novedad demostrada.
10. La salida no se declara lista para verdict sin pasar el handoff fail-closed
    hacia Skeptic y verdict.

## 6. Errores y degradación

- Entrada inválida, fuente inválida, ID duplicado, dominio insuficiente o límite
  inválido: fallo rápido con `ValueError` o `TypeError`, según la categoría.
- Excepción de una fuente: se conserva su entrada con
  `ok=False`, `error=SOURCE_EXCEPTION:<tipo>`, sin exponer el mensaje de la
  excepción ni secretos, y se continúa con las demás.
- Presupuesto global agotado antes de una fuente o durante un retry: se conserva
  su entrada con `ok=False`, `error=GLOBAL_BUDGET_EXHAUSTED` y no se inicia otra
  request.
- Respuesta de adapter ya fallida (`ok=False`): se conserva tal cual dentro de
  los límites del contrato; no se transforma en una fuente vacía.
- Respuesta con forma incompatible: se conserva como
  `SOURCE_CONTRACT_ERROR`, sin abortar silenciosamente el conjunto.

## 7. Handoff a Skeptic y verdict

El orden canónico es:

```text
cross-domain evidence -> SKEPTIC -> VERDICT
```

T07 solo puede validar la forma mínima del handoff mediante
`validate_downstream_handoff(results, skeptic=..., verdict=...)`:

- `skeptic` debe existir y contener al menos un `verdict` no vacío;
- `verdict` debe pertenecer a los valores existentes de `PriorArtVerdict`;
- `PROVEN_NEW` siempre se rechaza;
- un Skeptic con rechazo explícito se rechaza;
- un `SURVIVED_SEARCH` con `evidence_gaps` o con fuentes fallidas es una
  contradicción y se rechaza;
- ausencia de Skeptic, ausencia de verdict, contradicción o rechazo no produce
  una salida aceptada.

Este método es un guard de frontera, no el Skeptic ni el verdict engine. La
integración productiva no puede declararse verificada mientras P10-T08/P10-T09
no proporcionen consumidores reales y pruebas de contrato de extremo a extremo.

## 8. Fuera de alcance de T07

- Inferir analogías por similitud léxica, embeddings o un LLM.
- Crear o modificar `skeptic.py`, `verdict.py` o el orquestador P10.
- Emitir `PriorArtAssessment` o cualquier veredicto.
- Declarar novedad, originalidad, patentabilidad, libertad de operación o
  ausencia de prior art.
- Fusionar o deduplicar documentos de dominios distintos.
- Añadir fuentes, proveedores, credenciales, red, dependencias o servicios
  externos.
- Cambiar `Transport`, adapters existentes o el presupuesto de otras fases,
  salvo el binding temporal del presupuesto global de esta instancia.
- Cambiar P10-T08, P10-T09, P10-T10 o la cadena histórica de migración/GGUF.

## 9. Estado de decisión humana

La decisión de usar `KIND` exacto case-folded como proxy de dominio es una
aproximación determinista y explícita, no una ontología completa. Requiere
ratificación humana si el blueprint pretende analogías semánticas profundas,
normalización singular/plural o transferencia mecanismo-a-mecanismo. Hasta
entonces, P10-T07 permanece `PARTIAL` aunque sus tests de frontera pasen.
