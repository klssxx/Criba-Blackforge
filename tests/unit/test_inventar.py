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

    def _proponer(query: str, idea: dict, domain: dict | None) -> dict:
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
