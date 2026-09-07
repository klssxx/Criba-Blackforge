# P2 PERSONA SYSTEM — Especificación ejecutable

## Finalidad

P2 es la capa constitucional de razonamiento de CRIBA y Blackforge. No es un contrato mínimo. P3, P5, P6 y P10
dependen de que P2 produzca especialización real, comparabilidad, aislamiento, trazabilidad y evolución versionada.

## Invariantes ejecutables

1. Existen cuatro identificadores únicos de persona.
2. Cada persona tiene contrato especializado y núcleo común comparable.
3. Los inputs se copian defensivamente y el paquete original no se muta.
4. Las salidas de otras personas quedan excluidas del primer pase.
5. La misma entrada canónica produce el mismo fingerprint.
6. Cada prompt de persona produce un prompt fingerprint distinto.
7. Un backend ausente, inválido o no disponible genera fallback explícito y nunca un hecho confirmado.
8. La autorización ausente permanece `pending`.
9. La diversidad rechaza:
   - colapso total;
   - colapso parcial;
   - IDs duplicados;
   - contribución especializada insuficiente.
10. Una conclusión compartida puede aceptarse solo cuando existan justificaciones independientes.
11. El protocolo de equipo conserva disenso, atribución y reporte minoritario.
12. El feature flag `compound_personas` permanece desactivado por defecto.
13. P2 no crea ni implementa P3–P10.

## Gates

Los gates concretos están en:

```text
.autoregen/cloud/verification_manifest.json
```

## Evidencia semántica

Hermes + Hy3 debe producir un JSON conforme a:

```text
schemas/hy3_review.schema.json
```

No puede declarar `VERIFIED` solo por estilo, intuición o ausencia de errores. Todo hallazgo BLOCKER/HIGH debe incluir
archivo, símbolo o línea, evidencia y test de regresión propuesto.
