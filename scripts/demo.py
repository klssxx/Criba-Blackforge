from __future__ import annotations
import json
from pathlib import Path
from criba.engine import activate, build_prompt
from criba.storage import Storage

ROOT=Path(__file__).resolve().parents[1]
query=(ROOT/"examples"/"demo_query.txt").read_text(encoding="utf-8").strip()
store=Storage(ROOT/"artifacts"/"demo.sqlite3")
packet=activate(query,mode="strict")
store.save(query,packet,{"mode":"strict","demonstration":True})
simulated_response={"current":packet["selected_current"]["name"],"facts":["La consulta solicita seguridad y aprobación distribuida."],"hypotheses":[packet["experiment"]["falsifiable_hypothesis"]],"recommended_test":packet["experiment"]["variant"],"uncertainty":"Faltan datos sobre actores, umbrales y baseline.","final":"Empiece con un protocolo de capacidad limitada en sombra y no promueva ninguna autoridad hasta cumplir los guardrails."}
evidence=store.record_decision(packet["activation_id"],"AMPLIAR PRUEBA",[{"kind":"simulated_model_response","value":simulated_response}],"Demostración local simulada.")
reopened=store.get(packet["activation_id"])
result={"query":query,"selected_current":packet["selected_current"],"methods":packet["supporting_methods"],"rupture":packet["rupture"],"hypothesis":packet["experiment"]["falsifiable_hypothesis"],"experiment":packet["experiment"],"prompt":build_prompt(packet),"simulated_model_response":simulated_response,"evidence":evidence,"reopened_session":{"id":reopened["id"],"status":reopened["status"],"packet_matches":reopened["packet"]["activation_id"]==packet["activation_id"]}}
(ROOT/"artifacts").mkdir(exist_ok=True)
(ROOT/"artifacts"/"demo-result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({k:result[k] for k in ("selected_current","methods","hypothesis","reopened_session")},ensure_ascii=False,indent=2))

