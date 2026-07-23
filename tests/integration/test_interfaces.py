import json
from pathlib import Path
from criba.api import create_app
from criba.engine import activate
from criba.storage import Storage

QUERY="Prueba de seguridad de un flujo de aprobación para agentes de IA."
def test_persistence_reopen_and_compare(tmp_path):
    store=Storage(tmp_path/"criba.sqlite3"); a=activate(QUERY); b=activate(QUERY,mode="strict"); store.save(QUERY,a,{}); store.save(QUERY,b,{})
    assert store.get(a["activation_id"])["packet"]["activation_id"]==a["activation_id"]
    assert store.compare(a["activation_id"],b["activation_id"])["same_query_hash"]
def test_fastapi_packet(tmp_path):
    from fastapi.testclient import TestClient
    response=TestClient(create_app(tmp_path/"api.sqlite3")).post("/v1/activate",json={"query":QUERY})
    assert response.status_code==200 and response.json()["packet_type"]=="MANDATORY_MODEL_PACKET"

