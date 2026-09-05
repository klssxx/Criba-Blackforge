"""P10-T03: Google Patents-backed PatentScout contract."""
from __future__ import annotations

import json

from criba.intelligence.contracts import QueryVariant
from criba.intelligence.prior_art import PatentScout
from criba.intelligence.sources.google_patents import GooglePatentsSource
from criba.intelligence.sources.protocol import SourceContext
from criba.intelligence.sources.transport import Response, Transport

GOOGLE_PATENTS_JSON = json.dumps(
    {
        "results": {
            "cluster": [
                {
                    "result": [
                        {
                            "id": "patent/US123B2/en",
                            "patent": {
                                "publication_number": "US123B2",
                                "title": "  Thermal <b>management</b> apparatus  ",
                                "snippet": "A <b>thermal management</b> apparatus.",
                                "publication_date": "2026-01-02",
                                "priority_date": "2024-01-02",
                                "filing_date": "2025-01-02",
                                "inventor": "Ada Lovelace",
                                "assignee": "Example Labs",
                                "language": "en",
                            },
                        }
                    ]
                }
            ]
        }
    }
)


def test_patent_scout_normalizes_google_patents_with_query_provenance() -> None:
    transport = Transport(sender=lambda *args, **kwargs: Response(200, GOOGLE_PATENTS_JSON))
    source = GooglePatentsSource(SourceContext(transport=transport))

    result = PatentScout(source).search(QueryVariant("thermal management"), limit=1)

    assert result.ok is True
    assert result.source_id == "google_patents"
    assert len(result.documents) == 1
    document = result.documents[0]
    assert document.kind == "patent"
    assert document.title == "Thermal management apparatus"
    assert document.published == "2026-01-02"
    assert document.url == "https://patents.google.com/patent/US123B2/en"
    assert document.metadata["inventor"] == "Ada Lovelace"
    assert document.metadata["assignee"] == "Example Labs"
    assert document.provenance is not None
    assert document.provenance.url == document.url
    assert document.fragments[0].text == "A thermal management apparatus."
    assert result.query_text == "thermal management"


def test_google_patents_rejects_malformed_results_payload() -> None:
    transport = Transport(sender=lambda *args, **kwargs: Response(200, '{"results": {}}'))
    source = GooglePatentsSource(SourceContext(transport=transport))

    result = source.search("thermal management", limit=1)

    assert result.ok is False
    assert result.error == "bad payload: results.cluster is not a list"
