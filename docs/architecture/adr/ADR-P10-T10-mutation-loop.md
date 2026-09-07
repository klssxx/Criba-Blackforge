# ADR P10-T10 — Bounded mutation/re-search loop over PriorArtAssessment

**Estado:** `VERIFIED` localmente para P10-T10; P10 no está cerrada.
**Fecha:** 2026-09-05
**Alcance:** `run_prior_art_mutation_loop` de P10-T10 únicamente.

## Contexto

El pipeline canónico exige:

```text
CROSS-DOMAIN SCOUT -> SKEPTIC -> VERDICT -> T10 mutation/re-search
```

P10-T09 produce `PriorArtAssessment` con veredictos UNRESOLVED, PARTIAL_PRIOR_ART o SURVIVED_SEARCH, fallando cerrado sobre gaps. El ADR P10-T09 prohíbe inferir PROVEN_NEW.

Se requiere un loop P10-T10 que consuma el assessment, re-busque con variantes mutadas del mecanismo-candidato y respete el protocolo AdversarialSearchProtocol (max_prior_art_rounds, max_mutations_per_candidate).

## Decision

Se añade un componente puro y determinista:

```python
from criba.intelligence.prior_art import run_prior_art_mutation_loop

result = run_prior_art_mutation_loop(
    candidate=InventionCandidate(...),
    initial_assessment=PriorArtAssessment(...),
    protocol=AdversarialSearchProtocol(...),
    scout=CrossDomainScout([...]),
)
```

### Invariantes

1. **Fail-closed UNRESOLVED**: si el assessment inicial es UNRESOLVED, se lanza `ValueError("UNRESOLVED")`. No se muta ni re-busca.
2. **Only PARTIAL_PRIOR_ART or SURVIVED_SEARCH may be re-searched**: assessment con otro veredicto también falla con ValueError.
3. **Bounds respetados**: el loop respeta `protocol.can_execute(rounds_completed, mutations_completed)` y `protocol.can_mutate(mutations_completed)`.
4. **No PROVEN_NEW**: el veredicto final siempre es UNRESOLVED, PARTIAL_PRIOR_ART o SURVIVED_SEARCH.
5. **Determinismo**: las variantes mutadas son deterministas (dependientes del round), el orden de matches es estable, las queries se deduplican preservando orden.
6. **Reusa componentes existentes**: CrossDomainScout -> PriorArtSkeptic -> PriorArtVerdictEngine sin duplicar lógica.

### Output

`MutableResult` expone:
- `verdict`: str final (UNRESOLVED|PARTIAL_PRIOR_ART|SURVIVED_SEARCH)
- `rounds_completed`: int acotado por max_prior_art_rounds
- `mutations_completed`: int acbotado por max_mutations_per_candidate
- `queries_executed`: tuple[str, ...] deduplicado estable
- `assessments_by_round`: tuple[str, ...] de verdictos por ronda

## Fuera de alcance

- Similarity scoring, semantic matching, LLM, embeddings.
- Declarar novedad, originalidad, patentabilidad o PROVEN_NEW.
- External probes, providers, credenciales, red o mutaciones que no pasen por el protocolo.
- Cambiar T07/T08/T09, sources, transports o flags IIE.

## Evidencia

- RED observado: stub con NotImplementedError producía 5 failures (test_prior_art_mutation_loop.py).
- GREEN final: 5 tests P10-T10 + 45 tests P10 integrados + regresión CRIBA full suite = 953 passed, 1 warning.
- Ruff, mypy y compileall verdes en mutation_loop.py, __init__.py y test.
- COST=0; sin red, proveedor, credencial o escritura externa.

## Rollback

El write-set específico de T10 es `mutation_loop.py`, la adición de export en `prior_art/__init__.py`, `test_prior_art_mutation_loop.py` (reenpleado), este ADR y el journal. Revertir linealmente; no usar reset/clean en el árbol compartido.
