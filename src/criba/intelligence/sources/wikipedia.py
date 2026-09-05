"""Wikipedia product/company adapter (P10-T06, T017).

Free, no-key. Uses the public MediaWiki action API to search for
products, companies, and related concepts. Normalizes into EvidenceDocument.
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote_plus

from ..contracts import EvidenceDocument, EvidenceFragment, ProvenanceRecord, SourceQueryResult
from .protocol import IntelligenceSource


class WikipediaSource(IntelligenceSource):
    """T017 product/startup radar. Free, no-key. en.wikipedia.org/w/api.php."""

    SOURCE_ID = "wikipedia"
    NAME = "Wikipedia"
    KIND = "product"
    BASE_URL = "https://en.wikipedia.org/w/api.php"
    RATE_LIMIT_S = 0.5

    def _search(self, query: str, limit: int = 10, **params: Any) -> SourceQueryResult:
        res = SourceQueryResult(source_id=self.SOURCE_ID, query_text=query, ok=False)
        resp = self.context.transport.get(self.BASE_URL, params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": min(limit, 50),
            "format": "json",
            "origin": "*",
        })
        res.request_count += 1
        if resp.status != 200:
            res.error = f"HTTP {resp.status}"
            return res
        try:
            data = resp.json()
        except Exception as exc:
            res.error = f"bad json: {exc}"
            return res
        search_results = data.get("query", {}).get("search", [])
        if not isinstance(search_results, list):
            res.error = "bad payload: query.search is not a list"
            return res
        for item in search_results[:limit]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "")
            snippet = _strip_tags(str(item.get("snippet") or ""))
            page_id = str(item.get("pageid") or "")
            url = f"https://en.wikipedia.org/?curid={page_id}" if page_id else ""
            timestamp = str(item.get("timestamp") or "")
            doc = EvidenceDocument(
                doc_id=f"wp_{page_id}" if page_id else f"wp_{title}",
                source_id=self.SOURCE_ID,
                title=title[:500],
                kind="product",
                published=timestamp[:10],
                url=url,
                abstract=snippet[:2000],
                provenance=ProvenanceRecord(source_id=self.SOURCE_ID, url=url, method="api"),
                metadata={
                    "page_id": page_id,
                    "word_count": item.get("wordcount"),
                    "size": item.get("size"),
                },
            )
            if snippet:
                doc.fragments.append(EvidenceFragment(text=snippet[:500], locator="snippet"))
            res.documents.append(doc)
        res.ok = True
        return res


def _strip_tags(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", value)).strip()
