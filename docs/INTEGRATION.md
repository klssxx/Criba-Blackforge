# Integración con modelos

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

