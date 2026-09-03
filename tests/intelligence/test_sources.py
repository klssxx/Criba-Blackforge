"""P03 source tests: protocol, transport budget/retries, adapters with MOCK
transport (§101: no network in CI)."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from criba.intelligence.contracts import EvidenceDocument
from criba.intelligence.sources import (
    ArxivSource,
    ClinicalTrialsSource,
    CrossrefSource,
    EpoOpsSource,
    GitHubSource,
    NsfAwardsSource,
    OpenAlexSource,
)
from criba.intelligence.sources.protocol import IntelligenceSource, SourceContext
from criba.intelligence.sources.transport import Response, Transport, TransportBudget, BudgetExceeded


def ctx(sender, cache=None, creds=None, budget=None):
    return SourceContext(
        transport=Transport(sender=sender, budget=budget),
        cache_get=cache.cache_get if cache else None,
        cache_set=cache.cache_set if cache else None,
        credentials=creds or {},
    )


# -- fixtures: canned payloads -------------------------------------------------
OPENALEX_JSON = json.dumps({
    "results": [{
        "id": "https://openalex.org/W1", "doi": "https://doi.org/10.1/x",
        "title": "Photonic cooling for datacenters",
        "publication_year": 2026,
        "abstract_inverted_index": {"cooling": [0], "photonic": [1], "energy": [2]},
        "primary_location": {},
    }]
})

ARXIV_XML = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<entry><id>http://arxiv.org/abs/2601.00001</id><title>Radiative cooling meta</title>
<summary>We study passive radiative cooling.</summary><published>2026-01-02T00:00:00Z</published>
<author><name>A. Author</name></author></entry>
</feed>"""

GITHUB_JSON = json.dumps({
    "items": [{
        "full_name": "org/cool-sim", "description": "Datacenter cooling simulator",
        "html_url": "https://github.com/org/cool-sim", "created_at": "2025-11-01T00:00:00Z",
        "stargazers_count": 123, "language": "Python", "topics": ["cooling", "hpc"],
        "pushed_at": "2026-08-30T00:00:00Z", "url": "https://api.github.com/repos/org/cool-sim",
    }]
})

CROSSREF_JSON = json.dumps({
    "message": {
        "items": [{
            "DOI": "10.1234/example",
            "title": ["Deterministic metadata for cooling"],
            "URL": "https://doi.org/10.1234/example",
            "type": "journal-article",
            "published-online": {"date-parts": [[2026, 2, 3]]},
            "abstract": "<jats:p>Passive <b>cooling</b> metadata.</jats:p>",
            "author": [{"given": "Ada", "family": "Lovelace"}],
            "container-title": ["Journal of Determinism"],
            "is-referenced-by-count": 7,
        }]
    }
})

CLINICAL_TRIALS_JSON = json.dumps({
    "studies": [{
        "protocolSection": {
            "identificationModule": {"nctId": "NCT01234567", "briefTitle": "Cooling intervention trial"},
            "statusModule": {"overallStatus": "RECRUITING", "startDateStruct": {"date": "2026-01-15"}},
            "descriptionModule": {"briefSummary": "<b>Cooling</b> intervention for participants."},
            "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Example Hospital"}},
            "conditionsModule": {"conditions": ["Heat stress"]},
            "designModule": {"phases": ["PHASE2"]},
        }
    }]
})

NSF_AWARDS_JSON = json.dumps({
    "response": {
        "award": [{
            "id": "1234567",
            "title": "Efficient cooling research",
            "date": "01/15/2026",
            "abstractText": "<i>Funding</i> for thermal management.",
            "awardeeName": "Example University",
            "fundProgramName": "Energy Systems",
            "startDate": "02/01/2026",
            "expDate": "01/31/2029",
            "fundsObligatedAmt": "500000",
        }]
    }
})


def test_protocol_health_states():
    class NeedsKey(IntelligenceSource):
        SOURCE_ID, NAME, KIND = "x", "X", "science"
        REQUIRES_CREDENTIALS = ("api_key",)
        def _search(self, query, limit=10, **p):
            return SourceQueryResult(source_id=self.SOURCE_ID, query_text=query, ok=True)
    s = NeedsKey(ctx(None, creds={}))
    assert s.health() == "UNCONFIGURED"
    s2 = NeedsKey(ctx(None, creds={"api_key": "k"}))
    assert s2.health() == "AVAILABLE"


def test_transport_budget_blocks_requests():
    b = TransportBudget(max_requests=1)
    t = Transport(sender=lambda *a, **k: Response(200, "{}"), budget=b)
    assert t.get("https://x").status == 200
    with pytest.raises(BudgetExceeded):
        t.get("https://x")


def test_transport_retries_500_then_200():
    calls = {"n": 0}
    def flaky(url, params=None, timeout=0, headers=None):
        calls["n"] += 1
        return Response(500, "err") if calls["n"] == 1 else Response(200, "ok")
    t = Transport(sender=flaky, budget=TransportBudget(max_requests=10))
    assert t.get("https://x").status == 200
    assert calls["n"] == 2


def test_transport_429_reports_rate_limited(monkeypatch):
    # no sleep in tests
    monkeypatch.setattr(time, "sleep", lambda s: None)
    t = Transport(sender=lambda *a, **k: Response(429, "rate"),
                  budget=TransportBudget(max_requests=10))
    r = t.get("https://x")
    assert r.status == 429  # exhausted retries, returns last


def test_openalex_normalizes_documents():
    s = OpenAlexSource(ctx(lambda *a, **k: Response(200, OPENALEX_JSON)))
    r = s.search("photonic cooling")
    assert r.ok and len(r.documents) == 1
    d = r.documents[0]
    assert d.title.startswith("Photonic cooling")
    assert d.kind == "paper" and d.published == "2026"
    assert "photonic" in d.abstract


def test_crossref_normalizes_documents_and_strips_markup():
    s = CrossrefSource(ctx(lambda *a, **k: Response(200, CROSSREF_JSON)))
    r = s.search("passive cooling")
    assert r.ok and len(r.documents) == 1
    d = r.documents[0]
    assert d.kind == "paper" and d.published == "2026-02-03"
    assert d.metadata["doi"] == "10.1234/example"
    assert d.metadata["authors"] == ["Ada Lovelace"]
    assert d.metadata["citation_count"] == 7
    assert d.abstract == "Passive cooling metadata."


def test_crossref_rejects_non_list_items_payload():
    s = CrossrefSource(ctx(lambda *a, **k: Response(200, '{"message": {"items": {}}}')))
    r = s.search("passive cooling")
    assert not r.ok and r.error == "bad payload: message.items is not a list"


def test_clinical_trials_normalizes_study_and_reports_available_health():
    s = ClinicalTrialsSource(ctx(lambda *a, **k: Response(200, CLINICAL_TRIALS_JSON)))
    assert s.health() == "AVAILABLE"
    r = s.search("cooling")
    assert r.ok and len(r.documents) == 1
    d = r.documents[0]
    assert d.kind == "trial" and d.metadata["nct_id"] == "NCT01234567"
    assert d.metadata["lead_sponsor"] == "Example Hospital"
    assert d.metadata["phases"] == ["PHASE2"]
    assert d.abstract == "Cooling intervention for participants."


def test_nsf_awards_normalizes_grant_and_reports_available_health():
    s = NsfAwardsSource(ctx(lambda *a, **k: Response(200, NSF_AWARDS_JSON)))
    assert s.health() == "AVAILABLE"
    r = s.search("cooling")
    assert r.ok and len(r.documents) == 1
    d = r.documents[0]
    assert d.kind == "grant" and d.metadata["award_id"] == "1234567"
    assert d.metadata["program"] == "Energy Systems"
    assert d.metadata["amount"] == "500000"
    assert d.abstract == "Funding for thermal management."


def test_arxiv_parses_atom_xml():
    s = ArxivSource(ctx(lambda *a, **k: Response(200, ARXIV_XML)))
    r = s.search("radiative cooling")
    assert r.ok and len(r.documents) == 1
    d = r.documents[0]
    assert d.kind == "preprint" and d.published == "2026-01-02"
    assert d.metadata["authors"] == ["A. Author"]


def test_github_normalizes_and_detects_rate_limit():
    s = GitHubSource(ctx(lambda *a, **k: Response(403, "API rate limit exceeded")))
    r = s.search("cooling")
    assert not r.ok and r.error == "RATE_LIMITED"
    s2 = GitHubSource(ctx(lambda *a, **k: Response(200, GITHUB_JSON)))
    r2 = s2.search("cooling")
    assert r2.ok and r2.documents[0].metadata["stars"] == 123
    assert r2.documents[0].kind == "repository"


def test_epo_parses_ops_json():
    ops = json.dumps({"ops:world-patent-data": {"ops:biblio-search": {
        "ops:search-result": {"exchange-documents": [
            {"exchange-document": {"@doc-number": "EP123", "@date": "20260101",
             "bibliographic-data": {"invention-title": {"$": "Cooling apparatus"},
              "classifications-cpc": {"classification-cpc": [
                  {"@code": "G06F1/20"}, {"@code": "H05K7/20"}]}}}}]}}}})
    s = EpoOpsSource(ctx(lambda *a, **k: Response(200, ops)))
    r = s.search("datacenter cooling")
    assert r.ok and len(r.documents) == 1
    assert r.documents[0].metadata["cpc"] == ["G06F1/20", "H05K7/20"]


def test_cache_first_avoids_second_request():
    calls = {"n": 0}
    class MemCache:
        def __init__(self): self.d = {}
        def cache_get(self, k): return self.d.get(k)
        def cache_set(self, k, v, ttl=60): self.d[k] = v
    cache = MemCache()
    def sender(*a, **k):
        calls["n"] += 1
        return Response(200, OPENALEX_JSON)
    s = OpenAlexSource(ctx(sender, cache=cache))
    r1 = s.search("photonic cooling")
    r2 = s.search("photonic cooling")
    assert calls["n"] == 1 and len(r2.documents) == 1  # served from cache


def test_source_error_never_raises():
    def boom(*a, **k): raise ConnectionError("no net")
    s = OpenAlexSource(ctx(boom))
    r = s.search("x")
    assert not r.ok and "no net" in r.error


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
