"""MCP-compatible JSON-RPC stdio transport, with no network exposure."""
from __future__ import annotations
import json, sys
from .catalog import currents
from .engine import activate,build_prompt
from .selector import select
from .storage import Storage
TOOLS=[
 {"name":"activate_current","description":"Activate CRIBA before a final model response.","inputSchema":{"type":"object","properties":{"query":{"type":"string"},"current":{"type":"string","default":"auto"},"mode":{"type":"string","default":"balanced"},"supporting_methods":{"type":"integer","default":4},"context":{"type":"object"},"safety_level":{"type":"string","default":"strict"}},"required":["query"]}},
 {"name":"list_currents","description":"List current modules.","inputSchema":{"type":"object","properties":{}}},
 {"name":"explain_selection","description":"Explain deterministic selection.","inputSchema":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}},
 {"name":"run_criba","description":"Run and persist the CRIBA flow.","inputSchema":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}},
 {"name":"build_model_prompt","description":"Build an enriched model prompt.","inputSchema":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}},
 {"name":"record_decision","description":"Persist evidence and decision.","inputSchema":{"type":"object","properties":{"session_id":{"type":"string"},"status":{"type":"string"},"evidence":{}},"required":["session_id","status"]}},
 {"name":"compare_runs","description":"Compare two stored activations.","inputSchema":{"type":"object","properties":{"session_a":{"type":"string"},"session_b":{"type":"string"}},"required":["session_a","session_b"]}}
]
def call(name,args,store):
    if name=="list_currents": return currents()
    if name=="explain_selection": return select(args["query"],args.get("current","auto"))
    if name in {"activate_current","run_criba","build_model_prompt"}:
        packet=activate(**{k:v for k,v in args.items() if k in {"query","current","mode","supporting_methods","context","safety_level"}}); store.save(packet["original_query"],packet,args); return build_prompt(packet) if name=="build_model_prompt" else packet
    if name=="record_decision": return store.record_decision(args["session_id"],args["status"],args.get("evidence",[]),args.get("note",""))
    if name=="compare_runs": return store.compare(args["session_a"],args["session_b"])
    raise ValueError("Herramienta inexistente.")
def run_stdio(database=None):
    store=Storage(database)
    for line in sys.stdin:
        try:
            request=json.loads(line); method=request.get("method"); ident=request.get("id")
            if method=="initialize": result={"protocolVersion":"2024-11-05","serverInfo":{"name":"criba-current-engine","version":"0.1.0"},"capabilities":{"tools":{}}}
            elif method=="tools/list": result={"tools":TOOLS}
            elif method=="tools/call":
                result={"content":[{"type":"text","text":json.dumps(call(request["params"]["name"],request["params"].get("arguments",{}),store),ensure_ascii=False)}]}
            else: raise ValueError("Método MCP inexistente.")
            print(json.dumps({"jsonrpc":"2.0","id":ident,"result":result},ensure_ascii=False),flush=True)
        except Exception as exc: print(json.dumps({"jsonrpc":"2.0","id":request.get("id") if 'request' in locals() else None,"error":{"code":-32000,"message":str(exc)}},ensure_ascii=False),flush=True)

