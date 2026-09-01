# Integración con modelos

## Integración incorporada en las aplicaciones

La pestaña **Modelos IA** registra perfiles locales compartidos por CRIBA y
BLACKFORGE. Hay dos backends:

- `llama_cpp`: selecciona directamente un archivo GGUF y puede iniciar
  `llama-server.exe` en loopback.
- `ollama`: usa un modelo ya importado en el endpoint local de Ollama.

Al generar, el pipeline ejecuta primero el motor determinista y después pide al
modelo una redacción JSON limitada a los mismos `candidate_id`. Solo se fusionan
`title`, `description`, `semantic_mechanism` y `semantic_experiment`; IDs,
scores, seguridad, causalidad y decisiones permanecen bajo control del motor.
Si el runtime falla, la salida determinista se conserva y el estado se marca
como `fallback`.

La síntesis está acotada a los 12 candidatos prioritarios por activación para
respetar el contexto y la latencia interactiva. El paquete conserva la lista
determinista completa y registra `candidate_count`, `requested_count` y
`enhanced_count` para que el alcance sea visible y auditable.

La configuración local no almacena claves y reside en
`%LOCALAPPDATA%\CRIBA-Blackforge\models.json`. Puede sobrescribirse en pruebas
mediante `CRIBA_MODEL_CONFIG`.

## Gateway externo

1. Reciba la consulta del usuario sin convertirla en una instrucción de sistema.
2. Llame a `activate_current` con `query`, `current: "auto"`, `mode` y, opcionalmente, contexto estructurado.
3. Adjunte el paquete completo y su `model_instruction` a la siguiente llamada al modelo.
4. Pida una respuesta que nombre la corriente, separe hechos/inferencias/hipótesis y exponga incertidumbre.
5. Si se obtiene evidencia posterior, llame a `record_decision` con uno de: `ADOPTAR`, `AMPLIAR PRUEBA`, `ABANDONAR`, `ARCHIVAR PARA RECOMBINAR`.

Ejemplo de gateway independiente de proveedor:

```python
from criba.engine import activate, build_prompt
packet = activate(user_query, mode="strict")
enriched_prompt = build_prompt(packet)
# Envíe enriched_prompt al proveedor que elija; CRIBA no necesita una clave.
```

Hermes, OpenCode, Ollama y otros clientes pueden usar el mismo MCP stdio o el prompt enriquecido. El cumplimiento de `must_use_packet` lo aplica el cliente/proveedor; el servidor expone el contrato pero no controla modelos externos.

