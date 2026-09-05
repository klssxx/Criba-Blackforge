"""Deterministic claim extraction for the IIE claims sector (P05)."""
from __future__ import annotations

import re

from .contracts import Claim, EpistemicState, EvidenceDocument

# -- claims -------------------------------------------------------------------

_CLAIM_PATTERNS = [
    # "X reduces Y by 42%", "X enables Y", "limited to Z", "fails when W"
    (re.compile(r"([A-Za-z][\w\s-]{3,60}?)\s+(reduces|increases|enables|requires|improves|limits)\s+([\w\s-]{3,60})", re.I),
     EpistemicState.INFERENCE),
    (re.compile(r"([\w\s-]{3,60}?)\s+(fails?|degrades?|breaks?)\s+(when|under)\s+([\w\s-]{3,60})", re.I),
     EpistemicState.INFERENCE),
]


def extract_claims_from_fragments(doc: EvidenceDocument) -> list[Claim]:
    """Rule-based claim candidates from a document's fragments (created_by=rule)."""
    claims: list[Claim] = []
    for frag in doc.fragments:
        for pattern, state in _CLAIM_PATTERNS:
            m = pattern.search(frag.text)
            if m:
                claims.append(Claim(
                    text=m.group(0)[:300], epistemic_state=state,
                    evidence_doc_ids=(doc.doc_id,), fragment_ids=(frag.fragment_id,),
                    created_by="rule"))
                break  # one claim per fragment
    return claims
