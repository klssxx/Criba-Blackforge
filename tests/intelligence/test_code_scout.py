"""P10-T05: CodeScout contract against GitHub source adapter."""
from __future__ import annotations

import json

from criba.intelligence.contracts import QueryVariant
from criba.intelligence.prior_art import CodeScout
from criba.intelligence.sources.adapters import GitHubSource
from criba.intelligence.sources.protocol import SourceContext
from criba.intelligence.sources.transport import Response, Transport

GITHUB_JSON = json.dumps({
    "items": [
        {
            "full_name": "thermal-solutions/heat-sink",
            "description": "Advanced thermal management for electronics",
            "html_url": "https://github.com/thermal-solutions/heat-sink",
            "url": "https://api.github.com/repos/thermal-solutions/heat-sink",
            "created_at": "2023-05-15T10:30:00Z",
            "language": "Python",
            "stargazers_count": 42,
            "topics": ["thermal", "electronics"],
        }
    ]
})


def test_code_scout_normalizes_github_with_query_provenance() -> None:
    transport = Transport(sender=lambda *args, **kwargs: Response(200, GITHUB_JSON))
    source = GitHubSource(SourceContext(transport=transport))

    result = CodeScout(source).search(QueryVariant("thermal management"), limit=1)

    assert result.ok is True
    assert result.source_id == "github"
    assert len(result.documents) == 1
    document = result.documents[0]
    assert document.kind == "repository"
    assert document.title == "thermal-solutions/heat-sink"
    assert document.url == "https://github.com/thermal-solutions/heat-sink"
    assert document.metadata["language"] == "Python"
    assert document.metadata["stars"] == 42
    assert document.provenance is not None
    assert result.query_text == "thermal management"


def test_code_scout_respects_limit() -> None:
    payload = json.dumps({
        "items": [
            {
                "full_name": f"org/repo-{i}",
                "description": f"Repository {i}",
                "html_url": f"https://github.com/org/repo-{i}",
                "url": f"https://api.github.com/repos/org/repo-{i}",
                "created_at": "2023-01-01T00:00:00Z",
                "language": "Python",
                "stargazers_count": i,
            }
            for i in range(5)
        ]
    })
    transport = Transport(sender=lambda *args, **kwargs: Response(200, payload))
    source = GitHubSource(SourceContext(transport=transport))

    result = CodeScout(source).search(QueryVariant("heat transfer"), limit=2)

    assert result.ok is True
    assert len(result.documents) == 2


def test_code_scout_propagates_rate_limit() -> None:
    transport = Transport(sender=lambda *args, **kwargs: Response(403, "rate limit exceeded"))
    source = GitHubSource(SourceContext(transport=transport))

    result = CodeScout(source).search(QueryVariant("cooling"), limit=1)

    assert result.ok is False
    assert "RATE_LIMITED" in result.error
    assert result.query_text == "cooling"
