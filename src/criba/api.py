"""Loopback-only JSON API, documented at GET /docs. Uses no external framework."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from .catalog import currents,methods
from .constants import MAX_QUERY_CHARS
from .engine import activate,build_prompt
from .storage import Storage

class Handler(BaseHTTPRequestHandler):
    server_version="CRIBA/0.1"
    def _json(self,status,payload):
        body=json.dumps(payload,ensure_ascii=False).encode("utf-8"); self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def _body(self):
        length=int(self.headers.get("Content-Length","0"))
        if length>MAX_QUERY_CHARS*2: raise ValueError("Cuerpo excede el límite permitido.")
        raw=self.rfile.read(length)
        try: data=json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc: raise ValueError("JSON malformado.") from exc
        if not isinstance(data,dict): raise ValueError("El cuerpo debe ser un objeto JSON.")
        return data
    @property
    def store(self): return Storage(getattr(self.server,"database",None))
    def log_message(self,*args): pass # Never log query content or secrets.
    def do_GET(self):
        path=urlparse(self.path).path
        try:
            if path=="/health": return self._json(200,{"status":"ok","bind":"loopback"})
            if path=="/v1/currents": return self._json(200,currents())
            if path=="/v1/methods": return self._json(200,methods())
            if path.startswith("/v1/sessions/"): return self._json(200,self.store.get(path.rsplit("/",1)[1]))
            if path=="/docs": return self._json(200,{"openapi":"manual","endpoints":["POST /v1/activate","POST /v1/run","POST /v1/build-prompt","POST /v1/compare","POST /v1/decisions","GET /v1/currents","GET /v1/methods","GET /v1/sessions/{id}","GET /health"]})
            self._json(404,{"error":"Endpoint inexistente."})
        except ValueError as exc: self._json(404,{"error":str(exc)})
    def do_POST(self):
        path=urlparse(self.path).path
        try:
            data=self._body()
            if path in {"/v1/activate","/v1/run","/v1/build-prompt"}:
                packet=activate(data.get("query",""),data.get("current","auto"),data.get("mode","balanced"),data.get("supporting_methods",4),data.get("context",{}),data.get("safety_level","strict"),data.get("manual_methods"))
                self.store.save(packet["original_query"],packet,{k:data.get(k) for k in ("current","mode","supporting_methods","safety_level")})
                return self._json(200,{"packet":packet,"prompt":build_prompt(packet)} if path=="/v1/build-prompt" else packet)
            if path=="/v1/compare": return self._json(200,self.store.compare(data.get("session_a",""),data.get("session_b","")))
            if path=="/v1/decisions": return self._json(200,self.store.record_decision(data.get("session_id",""),data.get("status",""),data.get("evidence",[]),data.get("note","")))
            self._json(404,{"error":"Endpoint inexistente."})
        except (ValueError,TypeError) as exc: self._json(400,{"error":str(exc)})
        except Exception: self._json(500,{"error":"Error interno seguro."})

def serve(host="127.0.0.1",port=8765,database=None):
    if host not in {"127.0.0.1","localhost","::1"}: raise ValueError("Por seguridad la API solo escucha en loopback.")
    try:
        import uvicorn
        uvicorn.run(create_app(database),host=host,port=port,log_level="warning")
    except ImportError:
        server=ThreadingHTTPServer((host,port),Handler); server.database=database
        print(f"CRIBA API listening on http://{host}:{port} (docs: /docs)")
        try: server.serve_forever()
        except KeyboardInterrupt: pass
        finally: server.server_close()

def create_app(database=None):
    """FastAPI adapter with OpenAPI at /openapi.json and Swagger UI at /docs."""
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel, Field
    except ImportError:
        raise RuntimeError("FastAPI no está instalado; use el servidor estándar o requirements-optional.txt.")
    class Activation(BaseModel):
        query:str=Field(min_length=1,max_length=MAX_QUERY_CHARS)
        current:str="auto"; mode:str="balanced"; supporting_methods:int=Field(default=4,ge=1,le=8)
        context:dict={}; safety_level:str="strict"; manual_methods:list[str]|None=None
    class Compare(BaseModel): session_a:str; session_b:str
    class Decision(BaseModel): session_id:str; status:str; evidence:list|dict=[]; note:str=""
    app=FastAPI(title="CRIBA Current Engine",version="0.1.0",description="Local loopback CRIBA API. No external provider or keys.")
    def packet(data:Activation):
        try:
            result=activate(data.query,data.current,data.mode,data.supporting_methods,data.context,data.safety_level,data.manual_methods)
            Storage(database).save(result["original_query"],result,data.model_dump()); return result
        except ValueError as exc: raise HTTPException(400,str(exc))
    @app.get("/health")
    def health(): return {"status":"ok","bind":"loopback"}
    @app.get("/v1/currents")
    def get_currents(): return currents()
    @app.get("/v1/methods")
    def get_methods(): return methods()
    @app.get("/v1/sessions/{session_id}")
    def session(session_id:str):
        try: return Storage(database).get(session_id)
        except ValueError as exc: raise HTTPException(404,str(exc))
    @app.post("/v1/activate")
    def activate_endpoint(data:Activation): return packet(data)
    @app.post("/v1/run")
    def run_endpoint(data:Activation): return packet(data)
    @app.post("/v1/build-prompt")
    def prompt_endpoint(data:Activation):
        result=packet(data); return {"packet":result,"prompt":build_prompt(result)}
    @app.post("/v1/compare")
    def compare_endpoint(data:Compare):
        try: return Storage(database).compare(data.session_a,data.session_b)
        except ValueError as exc: raise HTTPException(404,str(exc))
    @app.post("/v1/decisions")
    def decision_endpoint(data:Decision):
        try: return Storage(database).record_decision(data.session_id,data.status,data.evidence,data.note)
        except ValueError as exc: raise HTTPException(400,str(exc))
    return app
