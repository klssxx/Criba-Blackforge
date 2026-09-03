"""IIE source adapters: free-first (§34). No paid APIs, no keys required.

OpenAlex (science), arXiv (preprints), GitHub (code radar), EPO OPS
(patents, no-key search endpoint). Each normalizes to EvidenceDocument.
"""
from __future__ import annotations

import re
from typing import Any

from ..contracts import EvidenceDocument, EvidenceFragment, ProvenanceRecord, SourceQueryResult
from .protocol import IntelligenceSource

_GENCounter = 0


def _new_doc_id(prefix: str) -> str:
    global _GENCounter
    _GENCounter += 1
    return f"{prefix}_{_GENCounter:08d}"


class OpenAlexSource(IntelligenceSource):
    """T010 scientific literature. Free, no key. api.openalex.org."""
    SOURCE_ID = "openalex"
    NAME = "OpenAlex"
    KIND = "science"
    BASE_URL = "https://api.openalex.org/works"
    RATE_LIMIT_S = 0.15  # polite pool: 10 req/s

    def _search(self, query: str, limit: int = 10, **params: Any) -> SourceQueryResult:
        res = SourceQueryResult(source_id=self.SOURCE_ID, query_text=query, ok=False)
        resp = self.context.transport.get(self.BASE_URL, params={
            "search": query, "per-page": min(limit, 50),
            "mailto": "research@example.org", "select": "id,doi,title,publication_year,abstract_inverted_index,primary_location"})
        res.request_count += 1
        if resp.status != 200:
            res.error = f"HTTP {resp.status}" + (f" ({resp.text[:120]})" if resp.status == 0 else "")
            return res
        try:
            data = resp.json()
        except Exception as exc:
            res.error = f"bad json: {exc}"
            return res
        for w in data.get("results", [])[:limit]:
            inv = w.get("abstract_inverted_index") or {}
            abstract = _inverted_index_to_text(inv)
            doc = EvidenceDocument(
                doc_id=_new_doc_id("oa"), source_id=self.SOURCE_ID,
                title=(w.get("title") or "")[:500], kind="paper",
                published=str(w.get("publication_year") or ""),
                url=(w.get("doi") or (w.get("id") or "")),
                abstract=abstract[:2000],
                provenance=ProvenanceRecord(source_id=self.SOURCE_ID, url=w.get("id") or "", method="api"),
                metadata={"openalex_id": w.get("id"), "doi": w.get("doi")},
            )
            if abstract:
                doc.fragments.append(EvidenceFragment(text=abstract[:500], locator="abstract"))
            res.documents.append(doc)
        res.ok = True
        return res


def _inverted_index_to_text(inv: dict) -> str:
    if not inv:
        return ""
    positions: list[tuple[int, str]] = []
    for word, idxs in inv.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort()
    return " ".join(w for _, w in positions[:120])


class ArxivSource(IntelligenceSource):
    """T010 preprints. Free Atom API."""
    SOURCE_ID = "arxiv"
    NAME = "arXiv"
    KIND = "science"
    BASE_URL = "http://export.arxiv.org/api/query"
    RATE_LIMIT_S = 3.0  # arXiv asks >=3s between requests

    def _search(self, query: str, limit: int = 10, **params: Any) -> SourceQueryResult:
        res = SourceQueryResult(source_id=self.SOURCE_ID, query_text=query, ok=False)
        resp = self.context.transport.get(self.BASE_URL, params={
            "search_query": f"all:{query}", "start": 0,
            "max_results": min(limit, 50), "sortBy": "relevance"})
        res.request_count += 1
        if resp.status != 200:
            res.error = f"HTTP {resp.status}"
            return res
        entries = re.findall(r"<entry>(.*?)</entry>", resp.text, re.S)
        for e in entries[:limit]:
            def _tag(t: str) -> str:
                m = re.search(rf"<{t}[^>]*>(.*?)</{t}>", e, re.S)
                return (m.group(1).strip() if m else "")
            title = _tag("title").replace("\n", " ")
            doc = EvidenceDocument(
                doc_id=_new_doc_id("ax"), source_id=self.SOURCE_ID,
                title=title[:500], kind="preprint",
                published=_tag("published")[:10],
                url=_tag("id"), abstract=_tag("summary")[:2000],
                provenance=ProvenanceRecord(source_id=self.SOURCE_ID, url=_tag("id"), method="api"),
                metadata={"authors": re.findall(r"<name>(.*?)</name>", e)[:10]},
            )
            res.documents.append(doc)
        res.ok = True
        return res


class GitHubSource(IntelligenceSource):
    """T014 GitHub innovation radar. Free unauthenticated: 10 req/min."""
    SOURCE_ID = "github"
    NAME = "GitHub"
    KIND = "code"
    BASE_URL = "https://api.github.com/search/repositories"
    RATE_LIMIT_S = 6.5  # unauth: ~10/min

    def _search(self, query: str, limit: int = 10, sort: str = "updated", **params: Any) -> SourceQueryResult:
        res = SourceQueryResult(source_id=self.SOURCE_ID, query_text=query, ok=False)
        headers = {}
        if self.context.has_credential("github_token"):
            headers["Authorization"] = f"token {self.context.credentials['github_token']}"
        resp = self.context.transport.get(self.BASE_URL, params={
            "q": query, "per_page": min(limit, 50), "sort": sort, "order": "desc"},
            headers=headers)
        res.request_count += 1
        if resp.status != 200:
            res.error = f"HTTP {resp.status}"
            if resp.status == 403 and "rate" in resp.text.lower():
                res.error = "RATE_LIMITED"
            return res
        data = resp.json()
        for item in data.get("items", [])[:limit]:
            doc = EvidenceDocument(
                doc_id=_new_doc_id("gh"), source_id=self.SOURCE_ID,
                title=(item.get("full_name") or ""), kind="repository",
                published=str(item.get("created_at") or "")[:10],
                url=item.get("html_url") or "",
                abstract=(item.get("description") or "")[:1000],
                provenance=ProvenanceRecord(source_id=self.SOURCE_ID,
                                            url=item.get("url") or "", method="api"),
                metadata={"stars": item.get("stargazers_count"),
                          "language": item.get("language"),
                          "topics": item.get("topics", [])[:20],
                          "pushed_at": item.get("pushed_at")},
            )
            res.documents.append(doc)
        res.ok = True
        return res


class EpoOpsSource(IntelligenceSource):
    """T001 patent search via EPO OPS free biblio search (no key)."""
    SOURCE_ID = "epo"
    NAME = "EPO OPS"
    KIND = "patents"
    BASE_URL = "https://ops.epo.org/3.2/rest-services/published-data/search"
    RATE_LIMIT_S = 1.0

    def _search(self, query: str, limit: int = 10, **params: Any) -> SourceQueryResult:
        res = SourceQueryResult(source_id=self.SOURCE_ID, query_text=query, ok=False)
        resp = self.context.transport.get(self.BASE_URL, params={"q": query, "Range": min(limit, 100)})
        res.request_count += 1
        if resp.status != 200:
            res.error = f"HTTP {resp.status}"
            return res
        # OPS returns XML (default) or JSON if Accept header set by caller
        try:
            data = resp.json()
            docs = data.get("ops:world-patent-data", {}).get(
                "ops:biblio-search", {}).get("ops:search-result", {}).get(
                "exchange-documents", [])
            for d in docs:
                doc_node = d.get("exchange-document", d if isinstance(d, dict) else {})
                bib = doc_node.get("bibliographic-data", {}) if isinstance(doc_node, dict) else {}
                title_obj = (bib.get("invention-title") or {})
                title = title_obj.get("$") if isinstance(title_obj, dict) else str(title_obj)
                cpc = [c.get("@scheme") and c.get("@code") or c.get("@code")
                       for c in bib.get("classifications-cpc", {}).get("classification-cpc", [])][:15]
                doc = EvidenceDocument(
                    doc_id=_new_doc_id("pat"), source_id=self.SOURCE_ID,
                    title=(title or doc_node.get("@doc-number", "patent"))[:500] if isinstance(doc_node, dict) else "patent",
                    kind="patent",
                    published=str(doc_node.get("@date", "")) if isinstance(doc_node, dict) else "",
                    url=f"https://register.epo.org/application?number={doc_node.get('@doc-number', '')}" if isinstance(doc_node, dict) else "",
                    provenance=ProvenanceRecord(source_id=self.SOURCE_ID, url="", method="api"),
                    metadata={"cpc": [c for c in cpc if c], "doc_number": doc_node.get("@doc-number") if isinstance(doc_node, dict) else None},
                )
                res.documents.append(doc)
        except Exception as exc:
            res.error = f"parse error: {exc}"
            return res
        res.ok = True
        return res
