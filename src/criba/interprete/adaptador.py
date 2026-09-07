"""Adaptador cloud: envía preguntas de expansión al modelo z.ai (glm-5.3-flash)
y parsea la respuesta estructurada.

Diseñado para aguantar interrupciones del plan Lite: si el modelo devuelve 429,
lanza un fallback que marca la idea como ``PENDIENTE`` (para reinterpretar
después) sin romper el pipeline. El prefiltrado es siempre determinista y no
requiere el modelo.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

from .protocolo import PREGUNTAS, protocolo_para

log = logging.getLogger(__name__)

ZAI_BASE = "https://api.z.ai/v1"
DEFAULT_MODEL = "glm-5.3-flash"
LOCAL_MODEL = os.getenv("CRIBA_LOCAL_MODEL", "poolside/laguna-s-2.1:free")
LOCAL_BASE = os.getenv("CRIBA_LOCAL_BASE", "https://api.nousresearch.com/v1")
TIMEOUT = 30.0


class LocalInterprete:
    """Interprete de fallback local usando poolside/laguna via Nous portal.
    Si NOUS_API_KEY no está configurado, usa scoring semántico offline (sin red)."""

    def __init__(self) -> None:
        self.api_key = os.getenv("NOUS_API_KEY")
        self.model = LOCAL_MODEL
        self.base = LOCAL_BASE
        self._offline = not self.api_key

    def interpretar(self, query: str, idea: dict[str, Any]) -> dict[str, Any]:
        if self._offline:
            return self._offline_fallback(query, idea)
        protocolo = protocolo_para(idea)
        prompt = self._build_prompt(query, idea, protocolo)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Eres un interprete de serendipia epistemológica. Respondes solo JSON válido."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 4096,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            with httpx.Client(timeout=TIMEOUT) as client:
                resp = client.post(f"{self.base}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            raw = content
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.endswith("```"):
                raw = raw[:-3]
            parsed = json.loads(raw)
            return {
                "labels": parsed.get("labels", []),
                "score": float(parsed.get("score", 0.0)),
                "veredicto": parsed.get("veredicto", "PENDIENTE"),
                "analisis": parsed.get("analisis", ""),
                "protocolo_aplicado": protocolo,
            }
        except Exception as e:
            log.error("Interpretación local fallida para idea %s: %s", idea.get("id"), e)
            return self._offline_fallback(query, idea)

    def proponer(
        self, query: str, idea: dict[str, Any], domain: dict[str, Any] | None = None,
        evidence: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Genera hipótesis con mecanismo a partir del cruce aplicado al problema.

        ``evidence``: documentos locales pertinentes recuperados del almacén;
        se entregan al intérprete para que la propuesta se apoye en ellos.
        Sin API key o ante fallo devuelve estado ``PENDIENTE_INTERPRETACION``
        sin fabricar contenido: una plantilla nunca se presenta como propuesta.
        """
        if self._offline:
            return {"estado": "PENDIENTE_INTERPRETACION", "hipotesis": "",
                    "mecanismo": "", "aportacion_por_tecnica": [], "supuestos": [],
                    "prueba_concreta": "", "error": "sin NOUS_API_KEY"}
        domain_title = str((domain or {}).get("title") or "general")
        evidence_block = ""
        for i, ev in enumerate((evidence or [])[:3], 1):
            title = str(ev.get("title") or "").strip()
            abstract = str(ev.get("abstract") or "").strip()
            if title or abstract:
                evidence_block += f"{i}. {title}: {abstract[:200]}\n"
        if evidence_block:
            evidence_block = (
                "\nEVIDENCIA LOCAL PERTINENTE (apóyate solo en la que sirva y "
                "cítala por número si la usas):\n" + evidence_block
            )
        bloqueo_block = ""
        bloqueo = idea.get("bloqueo") or {}
        if bloqueo.get("bloqueo"):
            lecciones = ""
            for i, lec in enumerate((bloqueo.get("lecciones_previas") or [])[:3], 1):
                lecciones += f"  {i}. {str(lec)[:200]}\n"
            if lecciones:
                lecciones = ("RESULTADOS PREVIOS REGISTRADOS (pueden cambiar la "
                             "decisión; cítalos si los usas):\n" + lecciones)
            bloqueo_block = f"""

BLOQUEO IDENTIFICADO (origen declarado: {bloqueo.get('origen_bloqueo', 'hipotesis')}):
{str(bloqueo.get('bloqueo'))[:400]}
Explicación: {str(bloqueo.get('explicacion_bloqueo', ''))[:300]}
Resultado buscado: {str(bloqueo.get('resultado_buscado', ''))[:200]}
{lecciones}
Tu propuesta debe atacar ESTA relación concreta. Cuando el bloqueo lo permita,
elige y declara UNA ruta de desbloqueo entre: eliminar_necesidad |
sustituir_mecanismo | desacoplar_dependencia. No cuestiones las restricciones
obligatorias: {str(bloqueo.get('restricciones_obligatorias', []))[:200]}.
Añade "ruta_desbloqueo" al JSON con la ruta elegida y su justificación."""
        prompt = f"""Aplica el cruce de técnicas a este problema concreto.

PROBLEMA: {query}
DOMINIO DE ACOPLAMIENTO: {domain_title}

CRUCE (dos operadores):
Técnica A: {idea.get('method1', idea.get('title', ''))}
Técnica B: {idea.get('method2', '')}
Título del cruce: {idea.get('title', '')}
{bloqueo_block}{evidence_block}
Responde ÚNICAMENTE con JSON válido (nada de markdown) con esta estructura:
{{
  "hipotesis": "propuesta específica para ESTE problema",
  "mecanismo": "cómo funciona causalmente, en términos del dominio",
  "aportacion_por_tecnica": ["qué aporta la técnica A aquí", "qué aporta la técnica B aquí"],
  "supuestos": ["supuesto cuestionable 1"],
  "prueba_concreta": "comparación mínima con métrica y condición de fracaso"
}}

El mecanismo es obligatorio y debe referirse al problema, no a los nombres
de las técnicas. Si el cruce no produce nada pertinente, dilo en hipótesis."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Eres un intérprete de cruces de técnicas. Respondes solo JSON válido."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 2048,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        pending = {"estado": "PENDIENTE_INTERPRETACION", "hipotesis": "",
                   "mecanismo": "", "aportacion_por_tecnica": [], "supuestos": [],
                   "prueba_concreta": "", "error": ""}
        try:
            with httpx.Client(timeout=TIMEOUT) as client:
                resp = client.post(f"{self.base}/chat/completions", json=payload, headers=headers)
            if resp.status_code == 429:
                pending["error"] = "plan_agotado_429"
                return pending
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            raw = content
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.endswith("```"):
                raw = raw[:-3]
            parsed = json.loads(raw)
            return {
                "estado": "PROPUESTA",
                "hipotesis": str(parsed.get("hipotesis", "")),
                "mecanismo": str(parsed.get("mecanismo", "")),
                "aportacion_por_tecnica": list(parsed.get("aportacion_por_tecnica", [])),
                "supuestos": list(parsed.get("supuestos", [])),
                "prueba_concreta": str(parsed.get("prueba_concreta", "")),
                "ruta_desbloqueo": str(parsed.get("ruta_desbloqueo", "")),
                "error": "",
            }
        except Exception as e:  # noqa: BLE001 - la propuesta nunca rompe el loop
            log.error("Propuesta fallida para idea %s: %s", idea.get("id"), e)
            pending["error"] = str(e)
            return pending

    def _offline_fallback(self, query: str, idea: dict[str, Any]) -> dict[str, Any]:
        """Scoring semántico offline (sin red) - usado cuando no hay API key o falla la red."""
        cv = idea.get("causal_variables", {})
        moved = [k for k in cv if cv.get(k)]
        dh = idea.get("prefilter", {}).get("dh", 0.6)
        text = f"{idea.get('description', '')} {idea.get('mechanism_causal', '')}".lower()
        labels: list[str] = ["tangible"]
        if len(moved) >= 3 and dh >= 0.6:
            labels.append("novedad_fronteriza")
        if any(w in text for w in ("contraintuit", "invertir", "al revés", "opuesto")):
            labels.append("contraintuitivo")
        local_vocab = {
            "imposible": "arriesgado", "utópico": "arriesgado",
            "absurdo": "arriesgado", "no obvio": "serendipia_forzada",
        }
        for term, label in local_vocab.items():
            if term in text and label not in labels:
                labels.append(label)
        if "arriesgado" in labels and dh >= 0.7:
            labels.append("serendipia_forzada")
        score = round(0.5 + 0.15 * len(moved) + 0.1 * (1 if "novedad_fronteriza" in labels else 0), 3)
        score = min(0.99, score)
        verdict = "tangible"
        for priority in ("novedad_fronteriza", "contraintuitivo", "serendipia_forzada", "arriesgado"):
            if priority in labels:
                verdict = priority
                break
        protocolo = protocolo_para(idea)
        return {"labels": labels, "score": score, "veredicto": verdict, "analisis": "[fallback-local-offline]", "protocolo_aplicado": protocolo}

    def _build_prompt(self, query: str, idea: dict[str, Any], protocolo: dict[str, Any]) -> str:
        preguntas = [p["pregunta"] for p in protocolo["preguntas"]]
        preguntas_texto = "\n".join(f"{i+1}. {p}" for i, p in enumerate(preguntas))
        return f"""Analiza esta idea bajo el protocolo de expansión epistemológica.

QUERY ORIGINAL: {query}
IDEA: {idea.get('title', 'N/A')}
DESCRIPCIÓN: {idea.get('description', 'N/A')}
MECANISMO CAUSAL: {idea.get('mechanism_causal', 'N/A')}
EJES CAUSALES MUTADOS: {idea.get('causal_axes_changed', [])}
DOMINIO: {idea.get('domain', 'general')}

Responde ÚNICAMENTE con JSON válido (nada de markdown) con esta estructura:
{{
  "labels": ["tangible", "novedad_fronteriza", "serendipia_forzada",
             "contraintuitivo", "arriesgado"],
  "score": 0.65,
  "veredicto": "tangible|novedad_fronteriza|serendipia_forzada|contraintuitivo|arriesgado",
  "analisis": "respuesta concisa a cada pregunta del protocolo"
}}

Responde solo las preguntas NO autocubiertas. Sé conciso pero riguroso.
Puntuación 0-1 (0.65 es el umbral mínimo de tangibilidad).

PREGUNTAS DE EXPANSIÓN:
{preguntas_texto}"""


class CloudInterprete:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL, base: str = ZAI_BASE) -> None:
        self.api_key = api_key
        self.model = model
        self.base = base.rstrip("/")

    @staticmethod
    def _build_prompt(query: str, idea: dict[str, Any], protocolo: dict[str, Any]) -> str:
        preguntas_texto = "\n".join(
            f"[{p['id']}] {p['pregunta']} (eje: {p['eje']})"
            + (" [AUTOCUBIERTO]" if p["auto_cubierta"] else "")
            for p in protocolo["preguntas"]
        )
        return f"""Eres un interprete de serendipia epistemológica. Evalúa la siguiente idea
generada por el motor CRIBA para la consulta: "{query}".

IDEA:
Título: {idea.get("title", "")}
Descripción: {idea.get("description", "")}
Mecanismo causal: {idea.get("mechanism_causal", "")}
Ruptura: {idea.get("rupture", "")}
Ejes causales movidos: {idea.get("causal_axes_changed", [])}
Score de convergencia CRIBA: {idea.get("convergence", {}).get("value_score", 0)}
Contención: {idea.get("prefilter", {}).get("dh", 0)}

Responde ÚNICAMENTE con JSON válido (nada de markdown) con esta estructura:
{{
  "labels": ["tangible", "novedad_fronteriza", "serendipia_forzada",
             "contraintuitivo", "arriesgado"],
  "score": 0.65,
  "veredicto": "tangible|novedad_fronteriza|serendipia_forzada|contraintuitivo|arriesgado",
  "analisis": "respuesta concisa a cada pregunta del protocolo"
}}

Responde solo las preguntas NO autocubiertas. Sé conciso pero riguroso.
Puntuación 0-1 (0.65 es el umbral mínimo de tangibilidad).

PREGUNTAS DE EXPANSIÓN:
{preguntas_texto}"""

    def interpretar(self, query: str, idea: dict[str, Any]) -> dict[str, Any]:
        """Envía la idea al modelo con el protocolo de expansion y parsea el JSON.
        En fallo de créditos/red, marca como PENDIENTE para reinterpretación posterior."""
        protocolo = protocolo_para(idea)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Eres un interprete de serendipia epistemológica. Respondes solo JSON válido."},
                {"role": "user", "content": self._build_prompt(query, idea, protocolo)},
            ],
            "temperature": 0.2,
            "max_tokens": 4096,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            with httpx.Client(timeout=TIMEOUT) as client:
                resp = client.post(f"{self.base}/chat/completions", json=payload, headers=headers)
            if resp.status_code == 429:
                log.warning("z.ai plan agotado (429); idea marcada PENDIENTE")
                return {"labels": [], "score": 0.0, "veredicto": "PENDIENTE_PLAN", "analisis": ""}
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            # Tolerante: extrae JSON incluso si viene envuelto en markdown
            raw = content
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.endswith("```"):
                raw = raw[:-3]
            parsed = json.loads(raw)
            return {
                "labels": parsed.get("labels", []),
                "score": float(parsed.get("score", 0.0)),
                "veredicto": parsed.get("veredicto", "PENDIENTE"),
                "analisis": parsed.get("analisis", ""),
                "protocolo_aplicado": protocolo,
            }
        except (httpx.HTTPError, json.JSONDecodeError, KeyError, ValueError) as e:
            log.error("Interpretación fallida para idea %s: %s", idea.get("id"), e)
            return {"labels": [], "score": 0.0, "veredicto": "ERROR_INTERPRETE",
                    "analisis": str(e), "protocolo_aplicado": protocolo}
