# Modelos locales GGUF en CRIBA + BLACKFORGE

## Qué resuelve esta capa

El motor original combina operadores de forma determinista y explicable. Eso
es útil para selección, diversidad y scoring, pero una plantilla no comprende
el problema como lo hace un modelo de lenguaje. La capa local nueva recibe el
problema y los candidatos ya seleccionados y devuelve para cada uno:

- un título concreto;
- una explicación de quién hace qué y para qué;
- un mecanismo causal;
- un experimento pequeño, medible y reversible.

El modelo no puede cambiar `candidate_id`, scores, decisiones ni metadatos de
seguridad. La respuesta se valida con Pydantic y cualquier fallo activa un
fallback determinista explícito.

CRIBA puede producir decenas de candidatos en una ronda. Para mantener la
respuesta dentro de un contexto de 8K y evitar muchos minutos de espera, la
capa semántica redacta los **12 candidatos mejor clasificados**. Todos los
candidatos y puntuaciones permanecen en el paquete; la interfaz indica el
recuento exacto (por ejemplo, `12/75`). BLACKFORGE genera como máximo 12 por
ronda y, por tanto, redacta la ronda completa.

## Opción recomendada: llama.cpp + GGUF

`llama.cpp` ejecuta directamente archivos GGUF y ofrece `llama-server`, un
servidor HTTP compatible con `/v1/chat/completions`. Su documentación oficial
incluye CPU, Vulkan y ejecución híbrida CPU/GPU:
<https://github.com/ggml-org/llama.cpp>.

En Windows puede instalarse con:

```powershell
winget install llama.cpp
```

Después:

1. Descarga un modelo instruct/chat en formato `.gguf`.
2. Abre **Modelos IA**.
3. Crea un perfil `GGUF local · llama.cpp`.
4. Selecciona el `.gguf` y `llama-server.exe`.
5. Mantén el endpoint `http://127.0.0.1:8080`.
6. Pulsa **Probar / iniciar modelo**, activa el perfil y guarda.

CRIBA inicia el servidor sin consola y solo en loopback. El proceso se cierra
cuando termina la aplicación que lo inició.

## Alternativa: Ollama

Ollama permite importar un GGUF con un `Modelfile` cuyo contenido sea:

```text
FROM C:\ruta\al\modelo.gguf
```

Luego se crea el alias:

```powershell
ollama create criba-local -f .\Modelfile
```

En la pestaña selecciona `Ollama local`, endpoint
`http://127.0.0.1:11434` y modelo `criba-local`. Referencia oficial:
<https://docs.ollama.com/import>.

## Modelo y cuantización recomendados

Para un equipo con 16 GB de RAM y entre 4 y 8 GB de VRAM:

- Punto de partida ágil: **Qwen3-4B Q4_K_M**.
- Mejor calidad si la velocidad híbrida CPU/GPU es aceptable:
  **Qwen3-8B Q4_K_M**.
- Evita 14B o superior como perfil interactivo por defecto en ese hardware.

Qwen3 ofrece español, seguimiento de instrucciones y modos thinking/no-thinking
en un mismo modelo. Pesos GGUF oficiales:

- <https://huggingface.co/Qwen/Qwen3-4B-GGUF>
- <https://huggingface.co/Qwen/Qwen3-8B-GGUF>

`Q4_K_M` es el equilibrio inicial; `Q5_K_M` puede mejorar ligeramente la
calidad si cabe con holgura. Empieza con contexto 8192 y capas GPU en
**Automático**. Si el controlador Vulkan no es estable, prueba un número de
capas menor o CPU antes de descartar el modelo.

## Niveles de reasoning

- **Rápido**: solicita thinking desactivado cuando el backend lo permite; una llamada.
  Útil para reformular y explorar con baja latencia.
- **Equilibrado**: solicita reasoning medio y hace una llamada estructurada. Es
  el valor predeterminado para nuevas ideas. Los modelos sin thinking continúan
  con la política de análisis incluida en el prompt.
- **Profundo**: solicita reasoning alto y realiza una segunda revisión del JSON.
  Úsalo para el ranking final o una decisión importante; aproximadamente duplica
  la latencia.

CRIBA nunca pide ni muestra una cadena de pensamiento. Solo conserva el JSON
final validado.

La generación se ejecuta fuera del hilo gráfico y admite hasta 300 segundos por
llamada para modelos híbridos CPU/GPU. La interfaz permanece utilizable; si el
runtime supera ese límite, CRIBA conserva la salida determinista y muestra el
fallback explícitamente.

## CLI

La CLI usa exactamente el mismo perfil y prompt que la GUI:

```powershell
uv run criba activate `
  --query "Reducir fraude sin perjudicar clientes legítimos" `
  --use-configured-model `
  --reasoning balanced

uv run criba blackforge `
  --query "Reducir fraude sin perjudicar clientes legítimos" `
  --seed 11 `
  --use-configured-model `
  --reasoning deep
```

La CLI facilita automatización, semillas y comparación de salidas; con el mismo
modelo y parámetros no tiene más calidad intrínseca que la interfaz gráfica.
