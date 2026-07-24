from __future__ import annotations
from typing import Any
from .catalog import methods

PREFERENCES={
 "strict":["diagnostico","verificacion","diseno_adversarial","decision_riesgo"],
 "creative":["morfologia","recombinacion","analogias","restricciones"],
 "adversarial":["diseno_adversarial","inversion","escenarios","verificacion"],
 "minimal":["diagnostico","arquitectura","verificacion","decision_riesgo"],
 "balanced":["diagnostico","inversion","arquitectura","verificacion"],
}
def select_methods(count: int=4, mode: str="balanced", manual: list[str]|None=None) -> list[dict[str, Any]]:
    if not 1 <= count <= 8: raise ValueError("supporting_methods debe estar entre 1 y 8.")
    available=methods(); by_id={m["id"]:m for m in available}; selected=[]; families=set()
    candidates=[by_id[x] for x in manual or [] if x in by_id] if manual else []
    preferred=PREFERENCES.get(mode,PREFERENCES["balanced"])
    candidates += sorted(available, key=lambda m:(preferred.index(m["family"]) if m["family"] in preferred else 99,m["id"]))
    for item in candidates:
        if item["family"] not in families:
            selected.append({**item,"reason":item["selection_reason"]}); families.add(item["family"])
        if len(selected)==count: break
    if len(selected)<count: raise ValueError("Biblioteca insuficiente para familias distintas.")
    return selected

