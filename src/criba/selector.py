"""Explainable keyword and signal selector. It is intentionally deterministic."""
from __future__ import annotations

import re
from typing import Any

from .catalog import currents, find_current

SIGNALS = {
 "absolute": ("siempre", "nunca", "garant", "imposible", "seguro", "fiable", "safety", "security"),
 "causal": ("causa", "causal", "correl", "tratamiento", "compar", "intervenci"),
 "novelty": ("innov", "disrupt", "alternativa", "ideas", "estanc"),
 "adversary": ("atac", "fraude", "advers", "seguridad", "seguro", "security", "gobernanza", "negoci", "compet"),
 "ai": ("ia", "ai", "modelo", "llm", "agente", "probabil", "oráculo"),
 "baseline": ("actual", "baseline", "sustitu", "reemplaz", "automat", "candidato"),
 "ablation": ("módulo", "regla", "agente", "dependencia", "componente", "complej"),
 "states": ("permiso", "estado", "transici", "flujo", "protocolo", "fase", "umbral", "aprob"),
 "time": ("tiempo", "longitud", "deriva", "mantenimiento", "reputación", "degrad"),
 "human": ("persona", "operador", "experto", "usuario", "aprobar", "fatiga", "equipo"),
 "transfer": ("interdisciplin", "aviación", "ecología", "inmunología", "radical", "dominio"),
 "meta": ("sesgo", "evaluador", "métrica", "jueces", "homogene", "proceso"),
}
WEIGHTS = {
 "falsacion_invariantes": {"absolute":36,"adversary":10,"states":7},
 "causal_contrafactual": {"causal":42,"baseline":12},
 "novedad_diversidad": {"novelty":45,"transfer":9},
 "coevolucion_atacante_defensor": {"adversary":48,"ai":6},
 "metamorficas_diferenciales": {"ai":42,"causal":5},
 "ejecucion_sombra": {"baseline":48,"states":5},
 "ablacion_reintroduccion": {"ablation":45,"baseline":5},
 "fronteras_estados_transiciones": {"states":48,"adversary":5},
 "deriva_longitudinal": {"time":48,"baseline":5},
 "factores_humanos": {"human":42,"states":5},
 "trasplante_interdisciplinar": {"transfer":48,"novelty":10},
 "metaexperimento_jueces": {"meta":48,"novelty":5},
}
BASE = 15

def _signals(query: str) -> dict[str, bool]:
    normalized = re.sub(r"[^\wáéíóúüñ]+", " ", query.casefold())
    return {name:any(token in normalized for token in tokens) for name,tokens in SIGNALS.items()}

def select(query: str, requested: str = "auto", allow_secondary: bool = False) -> dict[str, Any]:
    if not isinstance(query, str) or not query.strip(): raise ValueError("La consulta no puede estar vacía.")
    flags = _signals(query)
    scored=[]
    for current in currents():
        cid=current["id"]; contributions=[]; score=BASE
        for signal, weight in WEIGHTS[cid].items():
            if flags[signal]: score += weight; contributions.append(signal)
        score=min(100, score)
        reasons=[current["signal_reasons"][s] for s in contributions] or ["No hay señales dominantes; se aplica el baseline determinista."]
        scored.append({"current":cid,"name":current["name"],"score":score,"reasons":reasons})
    scored.sort(key=lambda x:(-x["score"], x["current"]))
    if requested != "auto":
        forced=find_current(requested); chosen=next(x for x in scored if x["current"]==forced["id"]); chosen["reasons"].insert(0,"Seleccionada manualmente por el usuario.")
    else: chosen=scored[0]
    rejected=[{"current":x["current"],"score":x["score"],"reason":x["reasons"][0]} for x in scored if x["current"]!=chosen["current"]]
    result={"selected_current":chosen["current"],"score":chosen["score"],"confidence":round(chosen["score"]/100,2),"selection_reasons":chosen["reasons"],"rejected_currents":rejected,"signals":flags}
    if allow_secondary and chosen["score"] < 60:
        secondary=next(x for x in scored if x["current"] != chosen["current"] and x["score"] >= 30)
        result["secondary_current"]={"id":secondary["current"],"score":secondary["score"],"reason":"Complementa una señal débil sin repetir el mecanismo principal."}
    return result
