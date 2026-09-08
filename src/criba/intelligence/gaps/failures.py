"""Deterministic failure mining from evidence fragments (P08-T04 / T070)."""
from __future__ import annotations

import re
from typing import Iterable

from ..contracts import EvidenceDocument, FailureCase

__all__ = [
    "FailureCaseExtractor",
    "FailureMiner",
    "extract_failures",
    "mine_failures",
]

_FAILURE_CUES = re.compile(
    r"\b(?:failure|failures|fails?|failed|breaks?|degrades?|crashes?|"
    r"stalls?|hangs?|cannot handle|can't handle|unable to|does not work|"
    r"doesn't work|unresolved|unrecoverable|unstable|unreliable|brittle)\b",
    re.IGNORECASE,
)
_RESOLVED_CUE = re.compile(
    r"\b(?:prevents?|avoids?|eliminates?|mitigates?|resolves?|resolved|"
    r"tolerates?|handles?|recovers? from|robust against)\b"
    r"[^.!?\n]*\b(?:failure|failures|error|errors|breakdown)\b",
    re.IGNORECASE,
)
_SENTENCE = re.compile(r"[^.!?\n]+(?:[.!?]|$)")
_MODE_PATTERNS = (
    re.compile(
        r"\bfailure\s+mode\s*(?:is|:)?\s*(?P<mode>[^.!?;\n]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:fails?|breaks?|degrades?|crashes?|stalls?|hangs?)\s+"
        r"(?P<mode>(?:when|under|with|without|if|during|on|for)\s+[^.!?;\n]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:cannot|can't|unable to|does not|doesn't)\s+"
        r"(?:handle|support|process|recover from)\s+"
        r"(?P<mode>[^.!?;\n]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bfailure\s+to\s+(?P<mode>[^.!?;\n]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?P<mode>(?:an?\s+)?(?:unresolved|unrecoverable|intermittent|"
        r"repeated|critical|systemic)?\s*(?:failure|error|breakdown)"
        r"(?:\s+(?:in|during|under|when|of)\s+[^.!?;\n]+)?)",
        re.IGNORECASE,
    ),
)


def _sentences(text: str) -> Iterable[str]:
    for match in _SENTENCE.finditer(text):
        sentence = " ".join(match.group(0).split())
        if sentence:
            yield sentence


def _failure_mode(sentence: str) -> str:
    for pattern in _MODE_PATTERNS:
        match = pattern.search(sentence)
        if match:
            mode = " ".join(match.group("mode").split()).strip(" ,:;-\t")
            if mode.lower().startswith(("a ", "an ")) and "failure" not in mode.lower()[:12]:
                mode = mode.split(" ", 1)[1]
            if mode:
                return mode[:240]
    return ""


class FailureCaseExtractor:
    """Extract auditable failure cases without network or model calls."""

    def extract(
        self, documents: Iterable[EvidenceDocument], *, topic: str = ""
    ) -> list[FailureCase]:
        failures: list[FailureCase] = []
        seen: set[tuple[str, str]] = set()
        for document in documents:
            for fragment in document.fragments:
                for sentence in _sentences(fragment.text):
                    if not _FAILURE_CUES.search(sentence) or _RESOLVED_CUE.search(sentence):
                        continue
                    if topic and topic.casefold() not in sentence.casefold():
                        continue
                    statement = sentence[:500]
                    key = (document.doc_id, statement.casefold())
                    if key in seen:
                        continue
                    seen.add(key)
                    failures.append(
                        FailureCase(
                            statement=statement,
                            failure_mode=_failure_mode(statement),
                            evidence_doc_ids=(document.doc_id,),
                        )
                    )
        failures.sort(key=lambda item: (item.evidence_doc_ids, item.statement.casefold()))
        return failures


FailureMiner = FailureCaseExtractor


def extract_failures(
    documents: Iterable[EvidenceDocument], *, topic: str = ""
) -> list[FailureCase]:
    """Convenience wrapper for deterministic failure-case extraction."""
    return FailureCaseExtractor().extract(documents, topic=topic)


def mine_failures(
    documents: Iterable[EvidenceDocument], *, topic: str = ""
) -> list[FailureCase]:
    """Alias emphasizing the blueprint's failure-mining terminology."""
    return extract_failures(documents, topic=topic)
