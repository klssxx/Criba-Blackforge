# Ejemplo 1 · Problema general — huerto urbano

Recorrido completo problema → cruce → hipótesis → antecedentes → dossier. Comandos reales verificados; donde aparece «requiere modelo» se marca explícitamente.

## 1. Definir el problema y el bloqueo

- **Resultado buscado:** reducir el consumo de agua del huerto sin penalizar rendimiento.
- **Bloqueo (origen: hipótesis):** el riego se calendariza por costumbre, no por estado del suelo; el calendario no observa la planta.
- **Restricciones obligatorias:** presupuesto de material < 100 €; sin obra.
- **Supuestos cuestionables:** «la frecuencia de riego es la variable relevante».

## 2. Ejecutar (sin red, sin modelo — salida honesta)

```bash
uv run python -m criba inventar "Reducir el consumo de agua de un huerto urbano" --offline --seed 42 --top 3
```

Salida esperada (offline): 3 candidatos con `score (heuristica_local)`, `interpretación: PENDIENTE_INTERPRETACION`, `prior-art: UNRESOLVED`. **No hay invención**: sin modelo no se fabrica hipótesis; sin mecanismo no se busca antecedente. El ledger queda en `%LOCALAPPDATA%\CRIBA-Blackforge\invention_ledger\verdicts.jsonl` con `seed/seed_source/run_id`.

## 3. Con modelo configurado (requiere proveedor autorizado)

El mismo comando sin `--offline` entrega al intérprete: problema + dominio de acoplamiento + ficha del cruce + evidencia local del almacén. Cada candidato devuelve `hipótesis`, `mecanismo`, `aportacion_por_tecnica`, `supuestos`, `prueba_concreta` y `ruta_desbloqueo`. La búsqueda de antecedentes parte del **mecanismo** (nunca del título); `SURVIVED_SEARCH` solo significa «sobrevivió a la búsqueda hecha».

## 4. Preparar dossier SUPRA

```bash
uv run python -m criba inventar "..." --dossier --seed 42
```

Genera `dossiers.jsonl` con la **prueba discriminante** (afirmación decisiva, alternativa explicativa, condición de fracaso) y estado `SUPRA_EJECUCION_PENDIENTE`. Ejemplo de prueba: medir humedad del suelo bajo riego por calendario vs riego por observación durante 14 días; si la diferencia no discrimina, el dossier no decide.

## 5. Aprendizaje

Tras ejecutar la prueba en el mundo real: `registrar_resultado(dossier_id, "positivo|negativo|indeterminado", condiciones)`. La próxima exploración del mismo problema recibe la lección en su prompt (`lecciones_previas`) — el circuito queda cerrado y trazable.

## Qué NO afirma este ejemplo

Nada sobre novedad universal: `UNRESOLVED`/`SURVIVED_SEARCH` tienen alcance limitado a las fuentes consultadas.
