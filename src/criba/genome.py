"""Controlled genome ontology for CRIBA innovation packets.

The backend owns a closed, versioned vocabulary. The model may PROPOSE a
classification but never controls the schema. Invalid values are coerced to
``unknown``; genuinely new concepts are parked in ``unclassified_properties``
for human review. The ontology is NEVER auto-extended.
"""
from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel, field_validator, ConfigDict

ONTOLOGY_VERSION = "1.0.0"

# MVP minimal genome: 5 closed dimensions (Comet's explicit scope).
ACTOR = [
    "end_user", "operator", "administrator", "autonomous_agent", "external_auditor",
    "organization", "infrastructure", "adversary", "regulator", "community", "unknown",
]
MECHANISM = [
    "elimination", "inversion", "isolation", "verification", "delegation", "prediction",
    "coordination", "consensus", "redundancy", "adaptation", "automation", "transformation",
    "market_exchange", "capability_proof", "unknown",
]
TOPOLOGY = [
    "centralized", "decentralized", "federated", "peer_to_peer", "hierarchical", "mesh",
    "pipeline", "hub_and_spoke", "cellular", "ephemeral", "hybrid", "unknown",
]
TRUST_MODEL = [
    "implicit", "identity_based", "capability_based", "evidence_based", "zero_trust",
    "reputation_based", "quorum_based", "adversarial", "unknown",
]
TIME_MODEL = [
    "synchronous", "asynchronous", "event_driven", "continuous", "periodic", "staged",
    "delayed", "ephemeral_per_operation", "unknown",
]

_ENUMS: Dict[str, List[str]] = {
    "actor": ACTOR,
    "mechanism": MECHANISM,
    "topology": TOPOLOGY,
    "trust_model": TRUST_MODEL,
    "time_model": TIME_MODEL,
}
_FIELDS = list(_ENUMS.keys())


class GenomeEvidence(BaseModel):
    """One classified field with the textual evidence that justifies it."""
    model_config = ConfigDict(extra="forbid")
    field: str
    value: str
    evidence_span: str


class UnclassifiedProperty(BaseModel):
    """A concept the model proposed that is NOT in the closed ontology.

    Never auto-extends the ontology. Parked for human review."""
    model_config = ConfigDict(extra="forbid")
    field: str
    value: str
    evidence: str
    source_idea: str = "unknown"
    status: str = "pending_review"


class Genome(BaseModel):
    """Closed genome. Every proposed value is normalized against the ontology."""
    model_config = ConfigDict(extra="forbid")
    ontology_version: str = ONTOLOGY_VERSION
    actor: List[str] = ["unknown"]
    mechanism: List[str] = ["unknown"]
    topology: List[str] = ["unknown"]
    trust_model: List[str] = ["unknown"]
    time_model: List[str] = ["unknown"]
    unclassified_properties: List[UnclassifiedProperty] = []

    @field_validator("actor", "mechanism", "topology", "trust_model", "time_model", mode="before")
    @classmethod
    def _normalize(cls, v, info):
        field = info.field_name
        allowed = _ENUMS[field]
        items = v if isinstance(v, list) else [v]
        out = []
        for item in items:
            if item is None:
                continue
            s = str(item).strip().lower()
            if s in allowed:
                out.append(s)
        return out or ["unknown"]


def classify(field: str, value: str) -> str:
    """Return the registered enum value or 'unknown'."""
    v = str(value).strip().lower()
    return v if v in _ENUMS.get(field, []) else "unknown"


def is_known(field: str, value: str) -> bool:
    return str(value).strip().lower() in _ENUMS.get(field, [])


def normalize_proposal(proposal: Dict[str, object], source_idea: str = "unknown") -> tuple[Genome, List[UnclassifiedProperty]]:
    """Build a Genome from a model-proposed dict, coercing invalid enums and
    parking unknown concepts. Returns (genome, parked_properties)."""
    data: Dict[str, list] = {f: ["unknown"] for f in _FIELDS}
    parked: List[UnclassifiedProperty] = []
    for field in _FIELDS:
        raw = proposal.get(field)
        if raw is None:
            continue
        values = raw if isinstance(raw, list) else [raw]
        kept, new = [], []
        for item in values:
            s = str(item).strip().lower()
            if s in _ENUMS[field]:
                kept.append(s)
            elif s and s != "unknown":
                new.append(UnclassifiedProperty(field=field, value=s,
                                                 evidence="propuesto por el modelo",
                                                 source_idea=source_idea, status="pending_review"))
        if kept:
            data[field] = kept
        parked.extend(new)
    genome = Genome(**data)
    genome.unclassified_properties = parked
    return genome, parked


def validate_evidence(genome: Genome, evidences: List[GenomeEvidence], source_idea: str = "unknown") -> List[str]:
    """Accept a model-proposed evidence list; coerce invalid fields, return warnings
    and park new concepts in unclassified_properties (with full structure)."""
    warnings: List[str] = []
    for ev in evidences:
        if ev.field not in _ENUMS:
            warnings.append(f"campo fuera de ontología: {ev.field}")
            genome.unclassified_properties.append(UnclassifiedProperty(
                field=ev.field, value=ev.value, evidence=ev.evidence_span,
                source_idea=source_idea, status="pending_review"))
            continue
        if ev.value.lower() not in _ENUMS[ev.field]:
            warnings.append(f"valor no registrado en {ev.field}: {ev.value} -> unknown")
            genome.unclassified_properties.append(UnclassifiedProperty(
                field=ev.field, value=ev.value, evidence=ev.evidence_span,
                source_idea=source_idea, status="pending_review"))
    return warnings
