"""Tests del loop `criba inventar` (offline, determinista, sin red)."""
from __future__ import annotations

import json

import pytest

from criba.intelligence.contracts import SourceQueryResult
from criba.intelligence.sources.transport import TransportBudget
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
