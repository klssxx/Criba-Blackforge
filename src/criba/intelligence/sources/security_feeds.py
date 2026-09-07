"""Fuentes de seguridad (perfil BLACKFORGE): CISA KEV y MITRE ATT&CK.

KEV: JSON oficial de CISA (catálogo completo, un documento por entrada
filtrada). ATT&CK: bundle STIX enterprise (descarga pesada — usar con
presupuesto y caché). Ambas fuentes heredan el gate offline del transporte.
"""
from __future__ import annotations

import re
from typing import Any

from .protocol import IntelligenceSource
from ..contracts import _new_id
from ..contracts import EvidenceDocument, EvidenceFragment, ProvenanceRecord, SourceQueryResult

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
ATTACK_URL = "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/enterprise-attack.json"


def _terms(query: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9\-.]+", query.lower()) if len(t) >= 3]


def _stable_or_new(stable_id: str, prefix: str) -> str:
    return stable_id if stable_id else _new_id(prefix)


class CisaKevSource(IntelligenceSource):
    """Vulnerabilidades explotadas conocidas. Sin clave; catálogo completo."""

    SOURCE_ID = "cisa_kev"
    NAME = "CISA KEV"
    KIND = "advisory"
    BASE_URL = KEV_URL
    RATE_LIMIT_S = 1.0

    def _search(self, query: str, limit: int = 10, **params: Any) -> SourceQueryResult:
        res = SourceQueryResult(source_id=self.SOURCE_ID, query_text=query, ok=False)
        resp = self.context.transport.get(self.BASE_URL)
        res.request_count += 1
        if resp.status != 200:
            res.error = f"HTTP {resp.status}"
            return res
        try:
            data = resp.json()
        except Exception as exc:
            res.error = f"bad json: {exc}"
            return res
        terms = _terms(query)
        entries = data.get("vulnerabilities") or []
        for entry in entries:
            if len(res.documents) >= limit:
                break
            if not isinstance(entry, dict):
                continue
            cve = str(entry.get("cveID") or "")
            vendor = str(entry.get("vendorProject") or "")
            product = str(entry.get("product") or "")
            name = str(entry.get("vulnerabilityName") or "")
            haystack = f"{cve} {vendor} {product} {name}".lower()
            if terms and not any(t in haystack for t in terms):
                continue
            doc = EvidenceDocument(
                doc_id=_stable_or_new(f"kev-{cve}" if cve else "", "kev"),
                source_id=self.SOURCE_ID,
                title=f"{cve}: {name}"[:500],
                kind="kev_entry",
                published=str(entry.get("dateAdded") or ""),
                url=f"https://nvd.nist.gov/view/vuln/detail?vulnId={cve}",
                abstract=str(entry.get("requiredAction") or "")[:1000],
                provenance=ProvenanceRecord(
                    source_id=self.SOURCE_ID, url=KEV_URL, method="api",
                    raw_hash=f"catalog:{data.get('catalogVersion', '')}",
                ),
                metadata={
                    "cveID": cve, "vendorProject": vendor, "product": product,
                    "dateAdded": entry.get("dateAdded"), "dueDate": entry.get("dueDate"),
                    "knownRansomwareCampaignUse": entry.get("knownRansomwareCampaignUse"),
                    "catalogVersion": data.get("catalogVersion"),
                    "dateReleased": data.get("dateReleased"),
                },
            )
            doc.fragments.append(EvidenceFragment(
                text=str(entry.get("requiredAction") or "")[:500], locator="requiredAction"))
            res.documents.append(doc)
        res.ok = True
        return res


class MitreAttackSource(IntelligenceSource):
    """Técnicas ATT&CK desde el bundle STIX oficial (enterprise)."""

    SOURCE_ID = "mitre_attack"
    NAME = "MITRE ATT&CK"
    KIND = "adversary"
    BASE_URL = ATTACK_URL
    RATE_LIMIT_S = 2.0
    TIMEOUT_S = 60.0

    def _search(self, query: str, limit: int = 10, **params: Any) -> SourceQueryResult:
        res = SourceQueryResult(source_id=self.SOURCE_ID, query_text=query, ok=False)
        resp = self.context.transport.get(self.BASE_URL)
        res.request_count += 1
        if resp.status != 200:
            res.error = f"HTTP {resp.status}"
            return res
        try:
            data = resp.json()
        except Exception as exc:
            res.error = f"bad json: {exc}"
            return res
        terms = _terms(query)
        objects = data.get("objects") or []
        for obj in objects:
            if len(res.documents) >= limit:
                break
            if not isinstance(obj, dict) or obj.get("type") != "attack-pattern":
                continue
            if obj.get("revoked") or obj.get("x_mitre_deprecated"):
                continue
            name = str(obj.get("name") or "")
            technique_id = str(obj.get("x_mitre_id") or "")
            haystack = f"{technique_id} {name}".lower()
            if terms and not any(t in haystack for t in terms):
                continue
            platforms = obj.get("x_mitre_platforms") or []
            description = str(obj.get("description") or "")
            doc = EvidenceDocument(
                doc_id=_stable_or_new(f"attack-{technique_id}" if technique_id else "", "attack"),
                source_id=self.SOURCE_ID,
                title=f"{technique_id}: {name}"[:500],
                kind="attack_technique",
                published=str(obj.get("created") or "")[:10],
                url=(f"https://attack.mitre.org/techniques/"
                     f"{technique_id.replace('.', '/')}") if technique_id else "",
                abstract=description[:2000],
                provenance=ProvenanceRecord(
                    source_id=self.SOURCE_ID, url=ATTACK_URL, method="api",
                    raw_hash=f"bundle:{data.get('spec_version', 'stix')}",
                ),
                metadata={
                    "technique_id": technique_id,
                    "platforms": [str(p) for p in platforms][:6],
                    "stix_id": obj.get("id"),
                    "modified": obj.get("modified"),
                },
            )
            if description:
                doc.fragments.append(EvidenceFragment(
                    text=description[:500], locator="description"))
            res.documents.append(doc)
        res.ok = True
        return res
