"""Tests del servicio «Actualizar fuentes» (mandato §6, Fase 2).

Cantidades reales, deduplicación honesta y offline que bloquea sin fingir
éxito. Todo con fuentes stub: cero red.
"""
from __future__ import annotations

import pytest

from criba.intelligence.contracts import EvidenceDocument, ProvenanceRecord, SourceQueryResult
from criba.intelligence.refresh import format_report, refresh_sources
from criba.intelligence.sources.transport import Transport, OfflineBlocked
from criba.intelligence.storage.store import IntelligenceStore


class _StubSource:
    """Fuente determinista inyectable: cuenta consultas, devuelve docs fijos."""

    SOURCE_ID = "stub"

    def __init__(self, documents: list[EvidenceDocument], fail_on: str | None = None) -> None:
        self._documents = documents
        self._fail_on = fail_on
        self.queries: list[str] = []

    def source_id(self) -> str:
        return self.SOURCE_ID

    def search(self, query: str, limit: int = 5, **params: object) -> SourceQueryResult:
        self.queries.append(query)
        if self._fail_on and self._fail_on in query:
            return SourceQueryResult(
                source_id=self.SOURCE_ID, query_text=query, ok=False, error="HTTP 503")
        return SourceQueryResult(
            source_id=self.SOURCE_ID, query_text=query, ok=True,
            documents=[d for d in self._documents if d.title][:limit])


def _doc(url: str, title: str = "T") -> EvidenceDocument:
    return EvidenceDocument(
        source_id="stub", title=title, kind="paper", url=url,
        provenance=ProvenanceRecord(source_id="stub", url=url, method="api"),
    )


def test_report_shows_real_counts(tmp_path) -> None:
    store = IntelligenceStore(str(tmp_path / "intel.sqlite3"))
    source = _StubSource([_doc("https://x/1"), _doc("https://x/2")])
    report = refresh_sources(["q1"], store=store, sources=[source])
    assert report["totals"]["documentos"] == 2
    assert report["totals"]["nuevos"] == 2
    assert report["per_source"][0]["ok"] == 1
    assert source.queries == ["q1"]


def test_duplicates_and_modifications_are_classified(tmp_path) -> None:
    store = IntelligenceStore(str(tmp_path / "intel.sqlite3"))
    doc_a = _doc("https://x/1", "titulo uno")
    refresh_sources(["q"], store=store, sources=[_StubSource([doc_a, doc_a])])
    doc_a2 = _doc("https://x/1", "titulo uno CAMBIADO")
    doc_b = _doc("https://x/2", "otro")
    report = refresh_sources(["q"], store=store, sources=[_StubSource([doc_a2, doc_b])])
    t = report["totals"]
    assert t["duplicados"] == 0  # el dup interno de la 1ª pasada no llega a la 2ª
    assert t["modificados"] == 1  # misma URL, contenido distinto
    assert t["nuevos"] == 1
    # y tras repetir todo idéntico: todo duplicado
    report3 = refresh_sources(["q"], store=store, sources=[_StubSource([doc_b])])
    assert report3["totals"]["duplicados"] == 1


def test_source_error_is_not_absence_of_results() -> None:
    source = _StubSource([_doc("https://x/1")], fail_on="malo")
    report = refresh_sources(["bueno", "malo"], sources=[source])
    summary = report["per_source"][0]
    assert summary["errores"] == 1
    assert summary["documents"] >= 1
    assert any("HTTP 503" in e for e in summary["errors"])


def test_offline_blocks_stub_transport() -> None:
    transport = Transport(offline=True)
    with pytest.raises(OfflineBlocked):
        transport.get("https://example.org")


def test_offline_report_declares_block(tmp_path) -> None:
    store = IntelligenceStore(str(tmp_path / "intel.sqlite3"))
    report = refresh_sources(["q"], profile="general", store=store, offline=True)
    wiki = next(s for s in report["per_source"] if s["source_id"] == "wikipedia")
    assert wiki["offline_blocked"]
    assert report["totals"]["documentos"] == 0


def test_format_report_mentions_real_numbers(tmp_path) -> None:
    store = IntelligenceStore(str(tmp_path / "intel.sqlite3"))
    report = refresh_sources(["q"], store=store,
                             sources=[_StubSource([_doc("https://x/9")])])
    text = format_report(report)
    assert "Nuevos: 1" in text
    assert "Errores: 0" in text


def test_refresh_rejects_blank_queries() -> None:
    with pytest.raises(ValueError):
        refresh_sources(["  "], sources=[])
