"""Adaptador LLM para CRIBA - permite usar modelos offline (Ollama) o cloud (API).

Este módulo conecta el motor CRIBA con modelos LLM para generar ideas
concretas en vez de plantillas mecánicas.

Modos soportados:
- offline: Ollama local (http://localhost:11434)
- cloud: API compatible con OpenAI (OpenAI, Anthropic via proxy, etc.)
- none: Modo actual sin modelo (plantillas mecánicas)
"""
from __future__ import annotations

import json
from typing import Any, Protocol

import httpx


# Configuración por defecto
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2"
DEFAULT_TIMEOUT = 120  # segundos


class LLMBackend(Protocol):
    """Interfaz para backends LLM."""

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Genera una respuesta del modelo."""
        ...

    def is_available(self) -> bool:
        """Verifica si el backend está disponible."""
        ...


class OllamaBackend:
    """Backend para Ollama local."""

    def __init__(self, url: str = DEFAULT_OLLAMA_URL, model: str = DEFAULT_OLLAMA_MODEL):
        self.url = url.rstrip("/")
        self.model = model
        self.client = httpx.Client(timeout=DEFAULT_TIMEOUT)

    def is_available(self) -> bool:
        try:
            r = self.client.get(f"{self.url}/api/tags")
            return r.status_code == 200
        except Exception:
            return False

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt

        r = self.client.post(f"{self.url}/api/generate", json=payload)
        r.raise_for_status()
        return str(r.json().get("response", ""))


class CloudBackend:
    """Backend para APIs cloud compatibles con OpenAI."""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1",
                 model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.Client(
            timeout=DEFAULT_TIMEOUT,
            headers={"Authorization": f"Bearer {api_key}"}
        )

    def is_available(self) -> bool:
        try:
            r = self.client.get(f"{self.base_url}/models")
            return r.status_code == 200
        except Exception:
            return False

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        r = self.client.post(f"{self.base_url}/chat/completions", json=payload)
        r.raise_for_status()
        return str(r.json()["choices"][0]["message"]["content"])


class NoneBackend:
    """Backend sin modelo - usa el motor determinista actual."""

    def is_available(self) -> bool:
        return True

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return "[Modo sin modelo: usar engine.activate() para generar ideas mecánicas]"


def create_backend(mode: str = "none", **kwargs: Any) -> LLMBackend:
    """Crea un backend LLM según el modo especificado.

    Args:
        mode: "offline" (Ollama), "cloud" (API), o "none" (sin modelo)
        **kwargs: Parámetros adicionales para el backend
    """
    if mode == "offline":
        url = kwargs.get("url", DEFAULT_OLLAMA_URL)
        model = kwargs.get("model", DEFAULT_OLLAMA_MODEL)
        return OllamaBackend(url=url, model=model)
    elif mode == "cloud":
        api_key = kwargs.get("api_key", "")
        base_url = kwargs.get("base_url", "https://api.openai.com/v1")
        model = kwargs.get("model", "gpt-4o-mini")
        return CloudBackend(api_key=api_key, base_url=base_url, model=model)
    else:
        return NoneBackend()


def build_llm_prompt(packet: dict[str, Any], methods: list[dict[str, Any]],
                     query: str) -> str:
    """Construye un prompt detallado para el LLM usando el paquete CRIBA.

    Este prompt incluye:
    - La consulta original
    - Los métodos seleccionados con sus descripciones
    - El espacio conocido y supuestos
    - Las rupturas identificadas
    - Instrucciones para generar ideas concretas
    """
    innovation = packet.get("innovation", {})
    known_space = innovation.get("known_space", [])
    assumptions = innovation.get("assumptions", [])
    ruptures = innovation.get("ruptures", [])

    methods_text = "\n".join([
        f"- {m['name']}: {m.get('selection_reason', '')}"
        for m in methods[:8]
    ])

    known_text = "\n".join([f"- {k}" for k in known_space[:5]])
    assumptions_text = "\n".join([f"- {a}" for a in assumptions[:4]])
    ruptures_text = "\n".join([
        f"- {r.get('operation', '?')}: {r.get('result', '?')[:100]}"
        for r in ruptures[:6]
    ])

    prompt = f"""Eres un experto en innovación y resolución de problemas.

CONSULTA ORIGINAL:
{query}

MÉTODOS DISPONIBLES:
{methods_text}

ESPACIO CONOCIDO:
{known_text}

SUPUESTOS IDENTIFICADOS:
{assumptions_text}

RUPTURAS PROPUESTAS:
{ruptures_text}

INSTRUCCIONES:
Genera 5 ideas concretas y accionables para resolver la consulta.
Cada idea debe:
1. Tener un título claro y descriptivo (máximo 10 palabras)
2. Incluir una descripción de 2-3 oraciones explicando cómo funciona
3. Mencionar qué método o ruptura aplica
4. Ser específica y ejecutable (no genérica)

Formato de salida (JSON):
{{
  "ideas": [
    {{
      "title": "Título de la idea",
      "description": "Descripción detallada",
      "method_applied": "Método utilizado",
      "feasibility": "alta/media/baja",
      "impact": "alto/medio/bajo"
    }}
  ]
}}
"""
    return prompt


def generate_ideas_with_llm(packet: dict[str, Any], methods: list[dict[str, Any]],
                            query: str, backend: LLMBackend) -> list[dict[str, Any]]:
    """Genera ideas usando el LLM y las convierte al formato CRIBA.

    Returns:
        Lista de ideas en formato CRIBA compatible con el motor.
    """
    if not backend.is_available():
        raise ConnectionError(f"Backend LLM no disponible: {type(backend).__name__}")

    prompt = build_llm_prompt(packet, methods, query)
    system_prompt = (
        "Eres un experto en innovación estructural. Genera ideas concretas, "
        "específicas y accionables. Nunca seas genérico. Siempre incluye "
        "detalles implementables."
    )

    response = backend.generate(prompt, system_prompt)

    try:
        # Intentar parsear como JSON
        ideas_data = json.loads(response)
        if isinstance(ideas_data, dict) and "ideas" in ideas_data:
            ideas_raw = ideas_data["ideas"]
        else:
            ideas_raw = ideas_data if isinstance(ideas_data, list) else []
    except json.JSONDecodeError:
        # Si no es JSON, intentar extraer ideas del texto
        ideas_raw = [{"title": "Idea generada", "description": response[:500],
                      "method_applied": "LLM", "feasibility": "media", "impact": "medio"}]

    # Convertir al formato CRIBA
    ideas = []
    for i, idea_raw in enumerate(ideas_raw[:5]):
        idea = {
            "id": f"LLM{i+1:02d}",
            "title": idea_raw.get("title", f"Idea LLM {i+1}"),
            "description": idea_raw.get("description", ""),
            "method_applied": idea_raw.get("method_applied", "LLM generation"),
            "feasibility": idea_raw.get("feasibility", "media"),
            "impact": idea_raw.get("impact", "medio"),
            "source": "llm",
        }
        ideas.append(idea)

    return ideas
