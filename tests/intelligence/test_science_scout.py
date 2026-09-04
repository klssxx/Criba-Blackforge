"""P10-T04: ScienceScout contract against scientific source adapters."""
from __future__ import annotations

import json

from criba.intelligence.contracts import QueryVariant
from criba.intelligence.prior_art import ScienceScout
from criba.intelligence.sources.adapters import OpenAlexSource
from criba.intelligence.sources.protocol import SourceContext
from criba.intelligence.sources.transport import Response, Transport

OPEN_ALEX_JSON = json.dumps({
    "results": [
        {
            "id": "https://openalex.org/W123",
            "doi": "https://doi.org/10.1234/example",
            "title": "Thermal management in compact systems",
            "publication_year": 2024,
            "abstract_inverted_index": {
                "thermal": [0],
                "management": [1],
                "system": [2],
            },
            "primary_location": {"source": "Journal of Heat Transfer"},
        }
    ]
})


def test_science_scout_normalizes_openalex_with_query_provenance() -> None:
    transport = Transport(sender=lambda *args, **kwargs: Response(200, OPEN_ALEX_JSON))
    source = OpenAlexSource(SourceContext(transport=transport))

    result = ScienceScout(source).search(QueryVariant("thermal management"), limit=1)

    assert result.ok is True
    assert result.source_id == "openalex"
    assert len(result.documents) == 1
    document = result.documents[0]
    assert document.kind == "paper"
    assert document.title == "Thermal management in compact systems"
    assert document.published == "2024"
    assert document.abstract == "thermal management system"
    assert document.metadata["doi"] == "https://doi.org/10.1234/example"
    assert document.provenance is not None
    assert result.query_text == "thermal management"


def test_science_scout_respects_limit() -> None:
    payload = json.dumps({
        "results": [
            {"id": f"https://openalex.org/W{i}", "title": f"Paper {i}",
             "publication_year": 2024, "abstract_inverted_index": {}}
            for i in range(5)
        ]
    })
    transport = Transport(sender=lambda *args, **kwargs: Response(200, payload))
    source = OpenAlexSource(SourceContext(transport=transport))

    result = ScienceScout(source).search(QueryVariant("heat transfer"), limit=3)

    assert result.ok is True
    assert len(result.documents) == 3


def test_science_scout_propagates_source_error() -> None:
    transport = Transport(sender=lambda *args, **kwargs: Response(503, ""))
    source = OpenAlexSource(SourceContext(transport=transport))

    result = ScienceScout(source).search(QueryVariant("battery cooling"), limit=1)

    assert result.ok is False
    assert "HTTP 503" in result.error
    assert result.query_text == "battery cooling"
