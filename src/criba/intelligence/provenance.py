"""IIE provenance + epistemic semantics (P05, blueprint §27/§102/§103).

Rules enforced here (deterministic — no LLM involved):
- A claim marked FACT must reference >=1 evidence doc; otherwise it is
  DOWNGRADED to INFERENCE and the assessment records it.
- grounded_claim_ratio: fraction of claims whose epistemic state is backed
  by at least one resolvable evidence document.
- content_hash: sha256 over normalized (title|abstract|url) for dedup.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .contracts import Claim, ClaimAssessment, EpistemicState, EvidenceDocument

__all__ = ["content_hash", "assess_claims", "ProvenanceValidator"]


def content_hash(doc: EvidenceDocument) -> str:
    basis = "|".join([
        (doc.title or "").strip().lower(),
        (doc.abstract or "")[:500].strip().lower(),
        (doc.url or "").strip(),
        " ".join((f.text or "")[:200] for f in doc.fragments)[:600],
    ])
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


@dataclass
class ProvenanceValidator:
    """§102: FACT claims must be grounded; ungrounded -> downgrade."""

    strict: bool = True  # strict: also require fragment ids

    def assess(self, claims: list[Claim], documents: list[EvidenceDocument]
               ) -> list[ClaimAssessment]:
        by_id = {d.doc_id: d for d in documents}
        out: list[ClaimAssessment] = []
        for c in claims:
            resolvable = [by_id[i] for i in c.evidence_doc_ids if i in by_id]
            grounded = bool(resolvable)
            if grounded and self.strict:
                frag_ids = {f.fragment_id for d in resolvable for f in d.fragments}
                grounded = bool(set(c.fragment_ids) & frag_ids) if c.fragment_ids else True
            if c.epistemic_state == EpistemicState.FACT and not grounded:
                c.epistemic_state = EpistemicState.INFERENCE
                out.append(ClaimAssessment(
                    claim_id=c.claim_id, grounded=False,
                    grounded_claim_ratio=0.0,
                    notes="downgraded FACT->INFERENCE: no resolvable evidence"))
            else:
                out.append(ClaimAssessment(
                    claim_id=c.claim_id, grounded=grounded,
                    grounded_claim_ratio=1.0 if grounded else 0.0,
                    notes="" if grounded else "no evidence refs"))
        return out

    def ratio(self, assessments: list[ClaimAssessment]) -> float:
        if not assessments:
            return 1.0
        return sum(1 for a in assessments if a.grounded) / len(assessments)


def assess_claims(claims: list[Claim], documents: list[EvidenceDocument]
                  ) -> tuple[list[ClaimAssessment], float]:
    """Convenience: assessments + global grounded_claim_ratio."""
    v = ProvenanceValidator()
    a = v.assess(claims, documents)
    return a, v.ratio(a)
