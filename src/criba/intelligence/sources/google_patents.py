"""Google Patents JSON adapter (P10-T03, no credentials observed required)."""
from __future__ import annotations

import hashlib
import html
import json
import re
from typing import Any
from urllib.parse import quote_plus

from ..contracts import (
    EvidenceDocument,
    EvidenceFragment,
    ProvenanceRecord,
    SourceQueryResult,
)
from .protocol import IntelligenceSource


class GooglePatentsSource(IntelligenceSource):
    """Normalize the public Google Patents query endpoint into IIE evidence."""

    SOURCE_ID = "google_patents"
    NAME = "Google Patents"
    KIND = "patent"
    BASE_URL = "https://patents.google.com/xhr/query"
    RATE_LIMIT_S = 1.0
    TIMEOUT_S = 20.0

    def capabilities(self) -> list[str]:
        return ["search", "patent_metadata"]

    def _search(self, query: str, limit: int = 10, **params: Any) -> SourceQueryResult:
        result = SourceQueryResult(source_id=self.SOURCE_ID, query_text=query, ok=False)
        if limit < 1:
            result.error = "limit must be at least 1"
            return result

        response = self.context.transport.get(
            self.BASE_URL,
            params={"url": f"q={quote_plus(query)}"},
            headers={"Accept": "application/json"},
        )
        result.request_count = 1
        if response.status != 200:
            result.error = f"HTTP {response.status} from Google Patents"
            return result
        try:
            payload = response.json()
        except (TypeError, ValueError) as exc:
            result.error = f"invalid Google Patents JSON: {exc}"
            return result

        documents, payload_error = _documents_from_payload(
            payload, limit=limit, source_id=self.SOURCE_ID
        )
        if payload_error:
            result.error = payload_error
            return result
        result.documents = documents
        result.ok = True
        return result


def _documents_from_payload(
    payload: Any, *, limit: int, source_id: str
) -> tuple[list[EvidenceDocument], str | None]:
    if not isinstance(payload, dict):
        return [], "bad payload: root is not an object"
    results = payload.get("results")
    if not isinstance(results, dict):
        return [], "bad payload: results is not an object"
    clusters = results.get("cluster")
    if not isinstance(clusters, list):
        return [], "bad payload: results.cluster is not a list"

    documents: list[EvidenceDocument] = []
    seen: set[str] = set()
    for cluster in clusters:
        if not isinstance(cluster, dict):
            continue
        entries = cluster.get("result")
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            patent = entry.get("patent")
            if not isinstance(patent, dict):
                continue
            publication_number = _clean_text(patent.get("publication_number"))
            if not publication_number or publication_number in seen:
                continue
            seen.add(publication_number)
            title = _clean_text(patent.get("title"))
            url = f"https://patents.google.com/patent/{publication_number}/en"
            snippet = _clean_text(patent.get("snippet"))
            language = _clean_text(patent.get("language")) or "en"
            metadata = {
                name: patent[name]
                for name in (
                    "inventor",
                    "assignee",
                    "priority_date",
                    "filing_date",
                    "publication_number",
                )
                if name in patent
            }
            raw = json.dumps(patent, sort_keys=True, separators=(",", ":"))
            fragment = (
                [EvidenceFragment(text=snippet, locator="snippet", language=language)]
                if snippet
                else []
            )
            documents.append(
                EvidenceDocument(
                    doc_id=f"{source_id}:{publication_number}",
                    source_id=source_id,
                    title=title,
                    kind="patent",
                    published=_clean_text(patent.get("publication_date")),
                    url=url,
                    language=language,
                    abstract=snippet,
                    fragments=fragment,
                    provenance=ProvenanceRecord(
                        source_id=source_id,
                        url=url,
                        method="api",
                        raw_hash=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
                    ),
                    metadata=metadata,
                )
            )
            if len(documents) >= limit:
                return documents, None
    return documents, None


def _clean_text(value: Any) -> str:
    text = html.unescape(re.sub(r"<[^>]*>", "", str(value or "")))
    return " ".join(text.split())
