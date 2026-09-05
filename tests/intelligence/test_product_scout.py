"""P10-T06: ProductScout contract against Wikipedia source adapter."""
from __future__ import annotations

import json

from criba.intelligence.contracts import QueryVariant
from criba.intelligence.prior_art import ProductScout
from criba.intelligence.sources.wikipedia import WikipediaSource
from criba.intelligence.sources.protocol import SourceContext
from criba.intelligence.sources.transport import Response, Transport

WIKIPEDIA_JSON = json.dumps({
    "query": {
        "search": [
            {
                "title": "Heat sink",
                "pageid": 12345,
                "snippet": "A <span class='searchmatch'>heat</span> sink is a passive heat exchanger.",
                "timestamp": "2024-01-15T10:30:00Z",
                "wordcount": 2500,
                "size": 25000,
            }
        ]
    }
})


def test_product_scout_normalizes_wikipedia_with_query_provenance() -> None:
    transport = Transport(sender=lambda *args, **kwargs: Response(200, WIKIPEDIA_JSON))
    source = WikipediaSource(SourceContext(transport=transport))

    result = ProductScout(source).search(QueryVariant("thermal management"), limit=1)

    assert result.ok is True
    assert result.source_id == "wikipedia"
    assert len(result.documents) == 1
    document = result.documents[0]
    assert document.kind == "product"
    assert document.title == "Heat sink"
    assert document.url == "https://en.wikipedia.org/?curid=12345"
    assert document.metadata["page_id"] == "12345"
    assert document.provenance is not None
    assert result.query_text == "thermal management"


def test_product_scout_respects_limit() -> None:
    payload = json.dumps({
        "query": {
            "search": [
                {"title": f"Product {i}", "pageid": i, "snippet": f"Snippet {i}",
                 "timestamp": "2024-01-01T00:00:00Z", "wordcount": 100, "size": 1000}
                for i in range(5)
            ]
        }
    })
    transport = Transport(sender=lambda *args, **kwargs: Response(200, payload))
    source = WikipediaSource(SourceContext(transport=transport))

    result = ProductScout(source).search(QueryVariant("heat transfer"), limit=2)

    assert result.ok is True
    assert len(result.documents) == 2


def test_product_scout_propagates_source_error() -> None:
    transport = Transport(sender=lambda *args, **kwargs: Response(503, ""))
    source = WikipediaSource(SourceContext(transport=transport))

    result = ProductScout(source).search(QueryVariant("battery cooling"), limit=1)

    assert result.ok is False
    assert "HTTP 503" in result.error
    assert result.query_text == "battery cooling"
