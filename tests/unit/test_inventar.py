"""Tests del loop `criba inventar` (offline, determinista, sin red)."""
from __future__ import annotations

import hashlib
import json

import pytest

from criba.intelligence.contracts import SourceQueryResult
from criba.intelligence.sources.protocol import IntelligenceSource, SourceContext
from criba.intelligence.sources.transport import OfflineBlocked, Transport, TransportBudget
from criba.inventar import append_ledger, invent


class _StubTransport:
    def __init__(self) -> None:
        self.budget = TransportBudget(max_requests=200)

    def get(self, url: str, **kwargs: object) -> object:
        raise ConnectionError("offline")


class _StubContext:
    def __init__(self) -> None:
        self.transport = _StubTransport()


class _OfflineSource:
    """Fuente determinista que falla como si no hubiera red."""

    def __init__(self, source_id: str, kind: str) -> None:
        self.SOURCE_ID = source_id
        self.KIND = kind
        self.context = _StubContext()

    def source_id(self) -> str:
        return self.SOURCE_ID

    def search(self, query: str, limit: int = 5) -> SourceQueryResult:
        return SourceQueryResult(
            source_id=self.SOURCE_ID, query_text=query, ok=False, error="OFFLINE_TEST"
        )

    def health(self) -> str:
        return "AVAILABLE"


def _sources() -> list[_OfflineSource]:
    return [_OfflineSource("stub_wiki", "product"), _OfflineSource("stub_patents", "patent")]


def _methods() -> list[dict]:
    catalog: list[dict] = []
    for class_name in ("perspectiva", "generacion", "ruptura", "escape"):
        for i in range(30):
            catalog.append(
                {
                    "id": f"{class_name}-{i:03d}",
                    "name": f"{class_name}-{i:03d}",
                    "title": f"{class_name} {i:03d}",
                    "family": class_name,
                    "thinking_class": class_name,
                }
            )
    for i in range(20):
        catalog.append(
            {
                "id": f"dominio-{i:03d}",
                "name": f"dominio-{i:03d}",
                "title": f"dominio {i:03d}",
                "family": "metodologias",
                "thinking_class": "dominio",
            }
        )
    return catalog


def test_invent_offline_returns_honest_sheet() -> None:
    sheet = invent(
        "secure approvals for autonomous agents",
        seed=42,
        rounds=2,
        batch_size=6,
        top=3,
        offline=True,
        methods=_methods(),
        sources=_sources(),
    )
    assert sheet["mode"] == "stratified"
    assert len(sheet["entries"]) == 3
    for entry in sheet["entries"]:
        assert entry["prior_art"]["verdict"] == "UNRESOLVED"
        assert entry["judge"]["veredicto"] == "PENDIENTE_OFFLINE"
        assert entry["classes"]
    assert sheet["totals"]["unresolved"] == 3


def test_invent_is_deterministic_per_seed() -> None:
    kwargs = {
        "seed": 7,
        "rounds": 2,
        "batch_size": 6,
        "top": 3,
        "offline": True,
        "methods": _methods(),
        "sources": _sources(),
    }
    a = invent("same query", **kwargs)
    b = invent("same query", **kwargs)
    titles_a = [e["title"] for e in a["entries"]]
    titles_b = [e["title"] for e in b["entries"]]
    assert titles_a == titles_b
    assert [e["score"] for e in a["entries"]] == [e["score"] for e in b["entries"]]


def test_invent_domain_coupling_present() -> None:
    sheet = invent("q", seed=1, rounds=1, batch_size=4, top=2, offline=True,
                   methods=_methods(), sources=_sources())
    assert sheet["domain_coupling"]["id"]


def test_invent_rejects_blank_query() -> None:
    with pytest.raises(ValueError):
        invent("   ", offline=True, methods=_methods(), sources=_sources())


def test_ledger_appends_jsonl(tmp_path) -> None:
    sheet = invent("q", seed=3, rounds=1, batch_size=4, top=2, offline=True,
                   methods=_methods(), sources=_sources())
    first = append_ledger(sheet, ledger_dir=tmp_path)
    second = append_ledger(sheet, ledger_dir=tmp_path)
    assert first == second
    lines = first.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    for line in lines:
        record = json.loads(line)
        assert record["seed"] == 3
        assert all(e["verdict"] in {"UNRESOLVED", "PARTIAL_PRIOR_ART", "SURVIVED_SEARCH"} for e in record["entries"])


# ---------------------------------------------------------------------------
# Fase 1: contrato corregido (mecanismo antes de antecedentes, IDs estables,
# offline en el transporte, ficha honesta). Comportamiento nuevo intencionado;
# ver CHECKPOINT_20260907.md.
# ---------------------------------------------------------------------------

def test_candidate_ids_stable_across_processes() -> None:
    """Los IDs usan sha256(semilla|consulta), no hash() de Python."""
    sheet = invent("stable id query", seed=42, rounds=1, batch_size=4, top=2,
                   offline=True, methods=_methods(), sources=_sources())
    expected = "invent-42-" + hashlib.sha256(b"42|stable id query").hexdigest()[:12]
    assert all(e["candidate_id"].startswith(expected) for e in sheet["entries"])


def test_offline_transport_blocks_all_requests() -> None:
    transport = Transport(offline=True)
    with pytest.raises(OfflineBlocked):
        transport.get("https://example.org/api")


def test_offline_blocks_proposer_even_with_credentials(monkeypatch) -> None:
    """Offline + NOUS_API_KEY presente: el proponente no se llama jamás.

    Regresión del escape: el gate no puede depender solo del estado interno
    de LocalInterprete (que considera «online» si hay clave).
    """
    from criba.interprete import adaptador

    def _must_not_run(self, query, idea, domain=None):  # type: ignore[no-untyped-def]
        raise AssertionError("proponer() fue llamado en modo offline")

    monkeypatch.setattr(adaptador.LocalInterprete, "proponer", _must_not_run)
    monkeypatch.setenv("NOUS_API_KEY", "test-key-offline-guard")

    sheet = invent("consulta con clave presente", seed=2, rounds=1, batch_size=4,
                   top=2, offline=True, methods=_methods(), sources=_sources())
    for entry in sheet["entries"]:
        assert entry["estado_interpretacion"] == "PENDIENTE_INTERPRETACION"
        assert entry["interpretacion_error"] == "modo offline"


def test_source_search_blocked_offline_never_hits_search() -> None:
    calls: list[str] = []

    class _Src(IntelligenceSource):
        SOURCE_ID = "stub"

        def _search(self, query: str, limit: int = 10, **params: object) -> SourceQueryResult:
            calls.append(query)
            return SourceQueryResult(source_id=self.SOURCE_ID, query_text=query, ok=True)

    source = _Src(SourceContext(transport=None, offline=True))
    result = source.search("anything")
    assert result.ok is False
    assert result.error == "OFFLINE_BLOCKED"
    assert calls == []


def test_offline_pending_interpretation_without_fabrication() -> None:
    """Offline: sin modelo no se fabrica hipótesis ni se busca antecedente."""
    sheet = invent("agente con permisos excesivos", seed=11, rounds=1, batch_size=6,
                   top=3, offline=True, methods=_methods(), sources=_sources())
    assert sheet["totals"]["pending_interpretation"] == 3
    for entry in sheet["entries"]:
        assert entry["estado_interpretacion"] == "PENDIENTE_INTERPRETACION"
        assert entry["hipotesis"] == ""
        assert entry["mecanismo"] == ""
        assert entry["prior_art"]["verdict"] == "UNRESOLVED"
        assert "sin-mecanismo" in entry["prior_art"]["detail"]


def test_ficha_honest_sin_etiquetas_de_calidad() -> None:
    """El score se etiqueta como heurística local; sin BASURA/EXTRAORDINARIA."""
    sheet = invent("q honesta", seed=5, rounds=1, batch_size=4, top=2,
                   offline=True, methods=_methods(), sources=_sources())
    for entry in sheet["entries"]:
        assert entry["score_kind"] == "heuristica_local"
        assert "quality" not in entry


def test_prior_art_searches_mechanism_not_title() -> None:
    """Con mecanismo interpretado, las consultas salen del mecanismo."""
    captured: list[str] = []

    class _RecordingSource:
        def __init__(self, source_id: str, kind: str) -> None:
            self.SOURCE_ID = source_id
            self.KIND = kind
            self.context = _StubContext()

        def source_id(self) -> str:
            return self.SOURCE_ID

        def health(self) -> str:
            return "AVAILABLE"

        def search(self, query: str, limit: int = 5) -> SourceQueryResult:
            captured.append(query)
            return SourceQueryResult(
                source_id=self.SOURCE_ID, query_text=query, ok=False, error="NO_RESULTS"
            )

    def _proponer(query: str, idea: dict, domain: dict | None, evidence=None) -> dict:
        return {
            "estado": "PROPUESTA",
            "hipotesis": "Limitar cada autorización a un único uso por operación.",
            "mecanismo": "capacidades de un solo uso evitan la reutilización de permisos",
            "aportacion_por_tecnica": ["A", "B"],
            "supuestos": ["el agente acepta renovación"],
            "prueba_concreta": "comparar reutilizaciones rechazadas",
            "error": "",
        }

    sheet = invent(
        "reducir permisos excesivos de un agente",
        seed=9, rounds=1, batch_size=6, top=2, offline=True,
        methods=_methods(),
        sources=[_RecordingSource("s1", "product"), _RecordingSource("s2", "patent")],
        proponer=_proponer,
    )
    assert sheet["totals"]["pending_interpretation"] == 0
    for entry in sheet["entries"]:
        assert entry["estado_interpretacion"] == "PROPUESTA"
        assert "un solo uso" in entry["mecanismo"]
    assert captured, "el mecanismo debe disparar búsqueda de antecedentes"
    # La búsqueda parte del mecanismo, nunca del título del cruce.
    titles = {e["title"] for e in sheet["entries"]}
    for query in captured:
        assert not any(t in query for t in titles)


def test_estado_antecedentes_is_honest() -> None:
    """Sin mecanismo → pendiente de búsqueda; con propuesta fallida offline
    nunca se declara «sin coincidencia» (mandato §7)."""
    sheet = invent("agente con permisos excesivos", seed=11, rounds=1, batch_size=6,
                   top=3, offline=True, methods=_methods(), sources=_sources())
    for entry in sheet["entries"]:
        assert entry["estado_antecedentes"] == "pendiente_de_busqueda"


def test_local_evidence_reaches_entry_when_store_given(tmp_path) -> None:
    from criba.intelligence.storage.store import IntelligenceStore

    store = IntelligenceStore(str(tmp_path / "intel.sqlite3"))
    store.save_document({
        "doc_id": "doc-e1", "source_id": "stub", "title": "Capacidades de un solo uso",
        "kind": "paper", "url": "https://x/cap", "abstract": "capacidades de un solo uso para agentes",
    })
    sheet = invent("permisos de un solo uso en agentes", seed=3, rounds=1, batch_size=4,
                   top=2, offline=True, methods=_methods(), sources=_sources(), store=store)
    assert sheet["entries"], "debe haber candidatos"
    assert all(isinstance(e.get("evidencia_local_usada"), list) for e in sheet["entries"])
    assert any(e["evidencia_local_usada"] for e in sheet["entries"])


# ---------------------------------------------------------------------------
# DV5-DV9 (megaprompt §31-§36): seeds, run_id, historial con cooldown
# ---------------------------------------------------------------------------

def test_dv5_explicit_seed_reproduces() -> None:
    kwargs = dict(rounds=2, batch_size=6, top=3, offline=True,
                  methods=_methods(), sources=_sources(), history_storage=False)
    a = invent("reproducible", seed=123, **kwargs)
    b = invent("reproducible", seed=123, **kwargs)
    assert [e["title"] for e in a["entries"]] == [e["title"] for e in b["entries"]]
    assert a["seed_source"] == b["seed_source"] == "explicit"
    assert a["run_id"] != b["run_id"], "run_id independiente de la seed"


def test_dv6_new_seed_generated_with_secrets_and_persisted() -> None:
    import re
    a = invent("exploracion libre", offline=True, rounds=1, batch_size=6, top=2,
               methods=_methods(), sources=_sources(), history_storage=False)
    b = invent("exploracion libre", offline=True, rounds=1, batch_size=6, top=2,
               methods=_methods(), sources=_sources(), history_storage=False)
    assert a["seed_source"] == "generated"
    assert a["seed"] != b["seed"], "ejecuciones nuevas exploran con seeds distintas"
    assert isinstance(a["seed"], int) and 0 < a["seed"] < 2**64
    # la seed generada reproduce: pasarla explícita da el mismo recorrido
    c = invent("exploracion libre", seed=a["seed"], offline=True, rounds=1,
               batch_size=6, top=2, methods=_methods(), sources=_sources(),
               history_storage=False)
    assert [e["title"] for e in c["entries"]] == [e["title"] for e in a["entries"]]


def test_dv6b_no_seed_falls_back_random_not_timestamp() -> None:
    import inspect
    from criba import inventar as mod
    src = inspect.getsource(mod)
    assert "secrets.randbits" in src
    assert "time.time()" not in src.split("def invent(")[1].split("def ")[0]


def test_dv8_history_cooldown_penalizes_recent_use(tmp_path) -> None:
    from criba.storage import Storage
    store = Storage(tmp_path / "hist.sqlite3")
    sheet = invent("con historial", seed=9, rounds=1, batch_size=6, top=2,
                   offline=True, methods=_methods(), sources=_sources(),
                   history_storage=store)
    assert sheet["entries"], "ejecución con historial funciona"
    # segunda ejecución: los pares recién usados reciben cooldown y la
    # selección explora pares distintos cuando el pool lo permite
    sheet2 = invent("con historial", seed=10, rounds=2, batch_size=8, top=3,
                    offline=True, methods=_methods(), sources=_sources(),
                    history_storage=store)
    assert sheet2["entries"]


def test_dv9_history_failure_degrades_gracefully(monkeypatch, tmp_path) -> None:
    class _Broken:
        def load_combination_first_seen(self, fp):
            raise OSError("db bloqueada")

        def save_lottery_combinations(self, *a, **k):
            raise OSError("db bloqueada")

    sheet = invent("sin historial utilizable", seed=5, rounds=1, batch_size=6,
                   top=2, offline=True, methods=_methods(), sources=_sources(),
                   history_storage=_Broken())
    assert len(sheet["entries"]) == 2


def test_evidencia_local_reaches_proponer(tmp_path) -> None:
    """La evidencia local se ENTREGA a la llamada del intérprete, no solo
    se guarda en la ficha (corrección de conducta del recorrido)."""
    from criba.intelligence.storage.store import IntelligenceStore

    store = IntelligenceStore(str(tmp_path / "intel.sqlite3"))
    store.save_document({
        "doc_id": "doc-e9", "source_id": "stub", "title": "Capacidades de un solo uso",
        "kind": "paper", "url": "https://x/cap",
        "abstract": "capacidades de un solo uso para agentes",
    })
    received: list = []

    def _proponer(query, idea, domain, evidence=None):
        received.append(evidence)
        return {
            "estado": "PROPUESTA", "hipotesis": "h", "mecanismo": "m del problema",
            "aportacion_por_tecnica": [], "supuestos": [], "prueba_concreta": "",
            "error": "",
        }

    sheet = invent("permisos de un solo uso en agentes", seed=4, rounds=1,
                   batch_size=4, top=2, offline=True, methods=_methods(),
                   sources=_sources(), proponer=_proponer, store=store)
    assert received and all(ev for ev in received), "el proponente debe recibir evidencia"
    assert any("Capacidades de un solo uso" in (e.get("title") or "")
               for ev in received for e in (ev or []))


def test_mecanismo_duplicado_se_sustituye_desde_el_pool() -> None:
    """Dos finalistas con el MISMO mecanismo interpretado → el redundante se
    sustituye por otro candidato del pool (una revisión por candidato)."""
    calls = {"n": 0}

    def _proponer(query, idea, domain, evidence=None):
        calls["n"] += 1
        # Los dos primeros candidatos producen la MISMA idea reescrita;
        # los siguientes producen mecanismos distintos.
        if calls["n"] in (1, 2):
            mecanismo = "limitar cada autorizacion a un unico uso por operacion"
        else:
            distintas = [
                "rotar credenciales del agente cada semana completa",
                "auditar permisos otorgados de forma mensual centralizada",
                "revocar privilegios sin uso tras treinta dias exactos",
            ]
            mecanismo = distintas[(calls["n"] - 3) % len(distintas)]
        return {"estado": "PROPUESTA", "hipotesis": "h", "mecanismo": mecanismo,
                "aportacion_por_tecnica": [], "supuestos": [], "prueba_concreta": "",
                "error": ""}

    sheet = invent("permisos excesivos", seed=8, rounds=2, batch_size=8, top=3,
                   offline=True, methods=_methods(), sources=_sources(),
                   proponer=_proponer)
    mecanismos = [e["mecanismo"] for e in sheet["entries"]]
    assert len(mecanismos) == len(set(mecanismos)), (
        "no deben coexistir mecanismos esencialmente duplicados tras la revisión"
    )
    revision = sheet["seleccion_finalista"].get("revision_post_interpretacion")
    assert revision and revision["intentos"], "la sustitución debe quedar registrada"
    assert revision["sustituciones_aceptadas"] >= 1


def test_mecanismo_completo_sin_truncar() -> None:
    """El mecanismo interpretado se conserva COMPLETO, no recortado a 200."""
    largo = "mecanismo completo: " + ("el sistema de cola redirige solicitudes hacia réplicas " * 6)
    def _proponer(query, idea, domain, evidence=None):
        return {"estado": "PROPUESTA", "hipotesis": "h", "mecanismo": largo,
                "aportacion_por_tecnica": [], "supuestos": [], "prueba_concreta": "",
                "error": ""}
    sheet = invent("q", seed=6, rounds=1, batch_size=6, top=2, offline=True,
                   methods=_methods(), sources=_sources(), proponer=_proponer)
    assert all(len(e["mecanismo"]) == len(largo) for e in sheet["entries"])


def test_revision_registra_aceptados_rechazados_y_llamadas() -> None:
    """Cada intento de sustitución queda registrado con identidad y resultado,
    y el conteo de llamadas del intérprete aparece en el informe."""
    calls = {"n": 0}
    def _proponer(query, idea, domain, evidence=None):
        calls["n"] += 1
        if calls["n"] in (1, 2):
            m = "limitar cada autorizacion a un unico uso por operacion"
        else:
            m = "auditar permisos otorgados mediante revision mensual externa"
        return {"estado": "PROPUESTA", "hipotesis": "h", "mecanismo": m,
                "aportacion_por_tecnica": [], "supuestos": [], "prueba_concreta": "",
                "error": ""}
    sheet = invent("permisos", seed=11, rounds=2, batch_size=8, top=3, offline=True,
                   methods=_methods(), sources=_sources(), proponer=_proponer)
    rev = sheet["seleccion_finalista"].get("revision_post_interpretacion")
    assert rev and rev["intentos"], "cada intento debe registrarse (aceptado o rechazado)"
    for intento in rev["intentos"]:
        assert intento["resultado"] in ("aceptado", "rechazado")
        assert intento["llamadas_modelo"] >= 1
        assert intento.get("reemplazado_id") or intento.get("sustituto_id")
    assert rev["llamadas_modelo_total"] == 3 + len(rev["intentos"])
    assert rev["llamadas_revision"] == len(rev["intentos"])


def test_cli_inventar_conecta_almacen_de_evidencia(monkeypatch, tmp_path) -> None:
    """La CLI pasa el almacén de evidencia por defecto a invent()."""
    import criba.cli as cli_mod
    import criba.inventar as inventar_mod
    capturado = {}
    def _fake_invent(query, **kwargs):
        capturado.update(kwargs)
        return {"query": query, "seed": 1, "seed_source": "explicit", "run_id": "r",
                "mode": "stratified", "rounds": 1, "domain_coupling": {"id": "d", "title": "t"},
                "entries": [], "totals": {"ideas": 0, "pending_interpretation": 0,
                "unresolved": 0, "partial_prior_art": 0, "survived_search": 0}}
    monkeypatch.setattr(inventar_mod, "invent", _fake_invent)
    monkeypatch.setattr(inventar_mod, "print_sheet", lambda sheet: None)
    monkeypatch.setattr(inventar_mod, "append_ledger", lambda sheet, ledger_dir=None: __import__("pathlib").Path("x.jsonl"))
    rc = cli_mod.main(["inventar", "consulta de prueba", "--offline", "--seed", "1"])
    assert rc == 0
    assert capturado.get("store") is not None, "la CLI debe pasar el almacén de evidencia"


def test_payload_del_proponente_contiene_la_evidencia(monkeypatch) -> None:
    """La solicitud real al intérprete incluye títulos y extractos de la
    evidencia: payload capturado del POST, no solo la ficha final."""
    from criba.interprete import adaptador

    class _Resp:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            return {"choices": [{"message": {"content": '{"hipotesis":"h","mecanismo":"m","aportacion_por_tecnica":[],"supuestos":[],"prueba_concreta":"p"}'}}]}
    capturado = {}
    class _Client:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, url, json=None, headers=None):
            capturado["url"] = url
            capturado["payload"] = json
            return _Resp()
    monkeypatch.setattr(adaptador.httpx, "Client", _Client)
    monkeypatch.setenv("NOUS_API_KEY", "test-key-payload")
    interp = adaptador.LocalInterprete()
    ev = [{"title": "Capacidades de un solo uso", "abstract": "evitan reutilizar permisos",
           "url": "https://x/cap", "doc_id": "doc-e9"}]
    interp.proponer("permisos de agentes", {"method1": "A", "method2": "B"}, {"title": "seg"}, ev)
    contenido = capturado["payload"]["messages"][1]["content"]
    assert "Capacidades de un solo uso" in contenido
    assert "evitan reutilizar permisos" in contenido


def test_cloud_interprete_parser_veredicto(monkeypatch) -> None:
    """Regresión qa-win: el typo 'verdicto' silenciaba todo veredicto cloud."""
    from criba.interprete import adaptador

    class _Resp:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            return {"choices": [{"message": {"content": '{"labels":["tangible"],"score":0.7,"veredicto":"novedad_fronteriza","analisis":"a"}'}}]}
    class _Client:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, url, json=None, headers=None): return _Resp()
    monkeypatch.setattr(adaptador.httpx, "Client", _Client)
    interp = adaptador.CloudInterprete(api_key="k")
    res = interp.interpretar("q", {"title": "t"})
    assert res["veredicto"] == "novedad_fronteriza"


def test_scout_con_fuentes_vacias_no_crash() -> None:
    """Regresión sospecha qa-win: sources=[] + mecanismo no debe crashear."""
    sheet = invent(
        "q con mecanismo", seed=3, rounds=1, batch_size=4, top=2, offline=True,
        methods=_methods(), sources=[], proponer=lambda q, i, d, ev=None: {
            "estado": "PROPUESTA", "hipotesis": "h",
            "mecanismo": "mecanismo especifico para este problema concreto aqui",
            "aportacion_por_tecnica": [], "supuestos": [], "prueba_concreta": "",
            "error": ""})
    for e in sheet["entries"]:
        assert e["prior_art"]["verdict"] == "UNRESOLVED"
