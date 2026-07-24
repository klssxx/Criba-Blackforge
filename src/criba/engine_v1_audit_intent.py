from __future__ import annotations
import json, uuid
from datetime import datetime, timezone
from typing import Any, Mapping
from .catalog import find_current
from .constants import MAX_QUERY_CHARS, VALID_MODES, VALID_DECISIONS, CURRENT_CATALOG_VERSION, SELECTOR_VERSION
from .methods import select_methods
from .selector import select

INSTRUCTION="""Antes de responder al usuario, aplica obligatoriamente el paquete CRIBA adjunto.

Corriente activada: {current}.

Utiliza sus resultados como estructura previa de la respuesta. No presentes el paquete como una verdad demostrada. Separa: 1. hechos aportados, 2. inferencias, 3. hipótesis, 4. experimentos propuestos.

No reveles cadena de pensamiento privada. Expón unicamente corriente activada, hallazgos relevantes, propuestas, riesgos, incertidumbre, prueba recomendada y respuesta final al usuario. No ignores contraejemplos o guardrails. Cuando falte informacion critica, no inventes datos."""

def _extract(query: str, context: Mapping[str, Any]) -> dict[str, Any]:
    constraints=context.get("constraints", [])
    if isinstance(constraints,str): constraints=[constraints]
    lowered=query.casefold()
    invariants=[]
    if any(x in lowered for x in ("seguro","seguridad","garant","sin depender","fiable")): invariants.append("La propiedad de seguridad declarada debe mantenerse bajo casos limite.")
    return {"problem":query.strip(),"actor":context.get("actor","No especificado"),"desired_result":context.get("desired_result","Disenar una respuesta o decision verificable."),"baseline":context.get("baseline","No aportado; establecer baseline antes de promover."),"constraints":constraints or ["No ejecutar acciones destructivas ni usar datos reales sin consentimiento."],"assumptions":context.get("assumptions",["La consulta no aporta todos los datos operativos necesarios."]),"invariants":invariants or ["La propuesta debe ser reversible antes de su adopcion."],"primary_metric":context.get("primary_metric","Tasa de cumplimiento de la hipotesis bajo prueba."),"guardrail_metrics":context.get("guardrail_metrics",["Incidentes de seguridad","Radio de dano","Reversibilidad"]),"uncertainties":context.get("uncertainties",["Contexto empirico insuficiente; las propuestas son hipotesis."])}

def _idea(method: Mapping[str, Any], current: Mapping[str, Any], query: str) -> dict[str, Any]:
    family=method["family"]
    mechanism={"diagnostico":"exponer supuestos medibles","inversion":"buscar el fallo minimo","sustraccion":"eliminar una dependencia","restricciones":"limitar complejidad","actores_roles":"separar facultades","incentivos":"alinear costes y recompensas","morfologia":"combinar dimensiones independientes","recombinacion":"integrar dos mecanismos","analogias":"trasplantar una regla causal","arquitectura":"compartimentar autoridad","gobernanza":"hacer reglas auditables","diseno_adversarial":"simular abuso seguro","escenarios":"probar frontera","prototipado":"validar en sombra","verificacion":"comprobar una relacion reproducible","decision_riesgo":"limitar dano y habilitar rollback"}[family]
    return {"method":method["name"],"method_id":method["id"],"proposal":f"Aplicar {method['name']} al problema: {query[:240]}","causal_mechanism":mechanism,"difference_from_existing":f"Aporta el mecanismo '{family}', distinto de las demas propuestas.","genealogy":[current["id"],method["id"]]}

def activate(query: str, current: str = "auto", mode: str = "balanced", supporting_methods: int = 4,
             context: dict[str, Any] | None = None, safety_level: str = "strict",
             manual_methods: list[str] | None = None) -> dict[str, Any]:
    if not isinstance(query,str) or not query.strip(): raise ValueError("La consulta no puede estar vacia.")
    if len(query)>MAX_QUERY_CHARS: raise ValueError(f"La consulta excede el limite de {MAX_QUERY_CHARS} caracteres.")
    if mode not in VALID_MODES: raise ValueError(f"Modo invalido: {mode}")
    if safety_level not in {"strict","standard"}: raise ValueError("safety_level debe ser strict o standard.")
    context=context or {}; selection=select(query,current); selected=find_current(selection["selected_current"]); methods=select_methods(supporting_methods,mode,manual_methods)
    contextualization=_extract(query,context); ideas=[_idea(m,selected,query) for m in methods]
    packet: dict[str, Any] = {"packet_type":"MANDATORY_MODEL_PACKET","activation_id":str(uuid.uuid4()),"timestamp":datetime.now(timezone.utc).isoformat(),"versions":{"currents":CURRENT_CATALOG_VERSION,"selector":SELECTOR_VERSION},"original_query":query,"selected_current":{"id":selected["id"],"name":selected["name"],"score":selection["score"],"selection_reasons":selection["selection_reasons"]},"selection":selection,"supporting_methods":[{"id":m["id"],"name":m["name"],"family":m["family"],"reason":m["reason"]} for m in methods],"contextualization":contextualization,"rupture":{"diagnostic_methods":[methods[0]["name"],methods[1]["name"] if len(methods)>1 else methods[0]["name"]],"main_assumption_attacked":contextualization["invariants"][0],"counterexample":f"Caso minimo: una entrada o transicion valida produce un resultado que viola '{contextualization['invariants'][0]}'.","rival_hypothesis":"El resultado depende de una condicion no observada o de incentivos desalineados.","adversarial_case":"Un actor intenta maximizar beneficio propio dentro de las reglas; la prueba se limita a datos simulados."},"ideas":ideas,"synthesis":{"selected_proposal":ideas[0]["proposal"],"combined_methods":[ideas[0]["method"],ideas[1]["method"]] if len(ideas)>1 else [ideas[0]["method"]],"why_selected":"Combina el supuesto mas critico con el mecanismo mas reversible; no se adopta sin evidencia."},"experiment":{"falsifiable_hypothesis":f"La variante basada en {selected['name']} mejora la metrica principal sin superar guardrails.","baseline":contextualization["baseline"],"variant":ideas[0]["proposal"],"changed_variable":ideas[0]["causal_mechanism"],"expected_evidence":"Mejora reproducible frente al baseline y ausencia de incumplimientos de guardrail.","primary_metric":contextualization["primary_metric"],"guardrails":contextualization["guardrail_metrics"],"damage_limit":"Solo datos sinteticos; cero cambios en proyectos reales; detener en el primer guardrail incumplido.","sandbox":"Entorno local temporal, aislado y sin credenciales ni red externa.","rollback":"Eliminar artefactos temporales y conservar unicamente el registro de evidencia.","promotion_criterion":"Dos ejecuciones reproducibles que superen el baseline sin guardrails incumplidos.","stop_criterion":"Cualquier guardrail incumplido, evidencia contradictoria relevante o timeout."},"decision":{"recommended_status":"AMPLIAR PRUEBA","justification":f"No hay evidencia empirica suficiente para ADOPTAR. Aplicar la prueba primero en sandbox.","confidence":round(min(0.8,selection["confidence"]*0.75),2)},"model_instruction":INSTRUCTION.format(current=selected["name"]),"response_contract":{"must_use_packet":True,"must_name_current":True,"must_separate_facts_and_hypotheses":True,"must_state_uncertainty":True,"must_not_reveal_private_chain_of_thought":True},"security":{"safety_level":safety_level,"no_command_execution":True,"no_network_by_default":True,"no_credentials_access":True}}
    if mode=="minimal":
        packet["minimal_summary"]={"current":selected["name"],"findings":selection["selection_reasons"][:3],"proposal":ideas[0]["proposal"],"test":packet["experiment"]["falsifiable_hypothesis"],"decision":packet["decision"]}
    return packet

def build_prompt(packet: Mapping[str, Any]) -> str:
    return "\n\n".join(["# Consulta original\n"+packet["original_query"],"# Instruccion CRIBA\n"+packet["model_instruction"],"# MANDATORY_MODEL_PACKET\n"+json.dumps(packet,ensure_ascii=False,indent=2),"# Contrato\nUsa obligatoriamente el paquete y no reveles razonamiento privado."])
