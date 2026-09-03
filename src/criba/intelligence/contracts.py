"""IIE contracts (P01-T03).

Layer L1. RULES (ADR-001): this module imports NOTHING from criba.* outside
criba.intelligence.contracts/enums. Pure dataclasses/enums only — no I/O, no
side effects, serializable to plain dicts (JSON-safe) for REST/MCP/state.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Sequence

__all__ = [
    "EpistemicState", "SourceHealth", "EvidenceDocument", "EvidenceFragment",
    "ProvenanceRecord", "Claim", "ClaimAssessment", "EntityNode", "EntityAlias",
    "RelationEdge", "TopicObservation", "Signal", "WeakSignal", "Gap",
    "Contradiction", "Limitation", "FailureCase", "ResurrectionCandidate",
    "WhiteSpaceCandidate", "Hypothesis", "InventionCandidate", "SourceDescriptor",
    "SourceCapability", "QueryPlan", "QueryVariant", "SourceQuery", "SourceQueryResult",
    "PriorArtQuery", "PriorArtMatch", "PriorArtAssessment", "NoveltyAssessment",
    "EvidenceAssessment", "ConfidenceAssessment", "FeasibilityAssessment",
    "TRLAssessment", "PrototypeabilityAssessment", "CompetitionAssessment",
    "PatentRiskAssessment", "OpportunityAssessment", "ScoreCard", "RankingResult",
    "IntelligenceRun", "IntelligencePacket",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_id(prefix: str) -> str:
    # Deterministic-looking opaque id; randomness OK here (not part of golden
    # packets — run ids are recorded, not compared).
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class EpistemicState(str, Enum):
    """Blueprint §27: an LLM can never move a claim to FACT by itself."""
    FACT = "FACT"
    INFERENCE = "INFERENCE"
    ASSUMPTION = "ASSUMPTION"
    HYPOTHESIS = "HYPOTHESIS"
    UNKNOWN = "UNKNOWN"


class SourceHealth(str, Enum):
    """Blueprint §33."""
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNCONFIGURED = "UNCONFIGURED"
    RATE_LIMITED = "RATE_LIMITED"
    UNAVAILABLE = "UNAVAILABLE"
    DISABLED = "DISABLED"


# ---------------------------------------------------------------------------
# Sources / query planning
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SourceDescriptor:
    source_id: str
    name: str
    kind: str                      # science | patents | code | ...
    base_url: str = ""
    requires_credentials: bool = False
    cost_class: str = "FREE_NETWORK"   # blueprint §125
    capabilities: tuple[str, ...] = ()  # see SourceCapability names
    external_requirements: tuple[str, ...] = ()
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id, "name": self.name, "kind": self.kind,
            "base_url": self.base_url, "requires_credentials": self.requires_credentials,
            "cost_class": self.cost_class, "capabilities": list(self.capabilities),
            "external_requirements": list(self.external_requirements), "enabled": self.enabled,
        }


@dataclass(frozen=True)
class SourceCapability:
    """What a source can do (used by capability discovery, §114/§115)."""
    name: str                      # e.g. "full_text_search"
    input_contracts: tuple[str, ...] = ()
    output_contracts: tuple[str, ...] = ()
    requires_network: bool = True
    requires_credentials: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "input_contracts": list(self.input_contracts),
            "output_contracts": list(self.output_contracts),
            "requires_network": self.requires_network,
            "requires_credentials": self.requires_credentials,
        }


@dataclass
class QueryVariant:
    """One mutated/expanded variant of the user query (T033/T035/T122)."""
    text: str
    language: str = "en"
    origin: str = "original"       # original|synonym|ontology|multilingual|mutation|decomposition
    technique_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "language": self.language, "origin": self.origin,
                "technique_ids": list(self.technique_ids)}


@dataclass
class SourceQuery:
    source_id: str
    variant: QueryVariant
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"source_id": self.source_id, "variant": self.variant.to_dict(), "params": self.params}


@dataclass
class QueryPlan:
    """Output of the query planner; input to retrieval."""
    run_id: str
    goal: str
    intent: str = "discovery"      # discovery|prior_art|radar|gap|invention|opportunity
    variants: list[QueryVariant] = field(default_factory=list)
    max_sources: int = 3
    max_queries: int = 6
    max_documents: int = 30
    max_requests: int = 20
    max_depth: int = 1
    max_runtime_s: float = 120.0
    paid_sources_allowed: bool = False
    preset: str = "BALANCED"       # QUICK|BALANCED|DEEP|EXHAUSTIVE (§35)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id, "goal": self.goal, "intent": self.intent,
            "variants": [v.to_dict() for v in self.variants],
            "budget": {
                "max_sources": self.max_sources, "max_queries": self.max_queries,
                "max_documents": self.max_documents, "max_requests": self.max_requests,
                "max_depth": self.max_depth, "max_runtime_s": self.max_runtime_s,
                "paid_sources_allowed": self.paid_sources_allowed, "preset": self.preset,
            },
        }


@dataclass
class SourceQueryResult:
    source_id: str
    query_text: str
    ok: bool
    documents: list[EvidenceDocument] = field(default_factory=list)   # fwd ref, resolved at runtime
    error: str = ""
    elapsed_s: float = 0.0
    request_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"source_id": self.source_id, "query_text": self.query_text, "ok": self.ok,
                "documents": [d.to_dict() for d in self.documents], "error": self.error,
                "elapsed_s": self.elapsed_s, "request_count": self.request_count}


# ---------------------------------------------------------------------------
# Evidence / provenance / claims
# ---------------------------------------------------------------------------

@dataclass
class ProvenanceRecord:
    """Blueprint §26/§103: every factual claim must trace to a source."""
    source_id: str
    retrieved_at: str = field(default_factory=_now_iso)
    url: str = ""
    license: str = ""
    method: str = ""               # api|crawl|file|derived
    raw_hash: str = ""             # sha256 of normalized raw payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceFragment:
    text: str
    locator: str = ""              # page/para/claim-number
    fragment_id: str = field(default_factory=lambda: _new_id("frag"))
    language: str = "en"
    epistemic_state: EpistemicState = EpistemicState.INFERENCE

    def to_dict(self) -> dict[str, Any]:
        return {"fragment_id": self.fragment_id, "text": self.text, "locator": self.locator,
                "language": self.language, "epistemic_state": self.epistemic_state.value}


@dataclass
class EvidenceDocument:
    doc_id: str = field(default_factory=lambda: _new_id("doc"))
    source_id: str = ""
    title: str = ""
    kind: str = "document"         # paper|patent|repo|product|dataset|...
    published: str = ""            # ISO date or year
    url: str = ""
    language: str = "en"
    abstract: str = ""
    fragments: list[EvidenceFragment] = field(default_factory=list)
    provenance: ProvenanceRecord | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id, "source_id": self.source_id, "title": self.title,
            "kind": self.kind, "published": self.published, "url": self.url,
            "language": self.language, "abstract": self.abstract,
            "fragments": [f.to_dict() for f in self.fragments],
            "provenance": self.provenance.to_dict() if self.provenance else None,
            "metadata": self.metadata,
        }


@dataclass
class Claim:
    claim_id: str = field(default_factory=lambda: _new_id("clm"))
    text: str = ""
    epistemic_state: EpistemicState = EpistemicState.INFERENCE
    evidence_doc_ids: tuple[str, ...] = ()
    fragment_ids: tuple[str, ...] = ()
    technique_ids: tuple[str, ...] = ()
    created_by: str = "rule"       # rule|model:<name>

    def to_dict(self) -> dict[str, Any]:
        return {"claim_id": self.claim_id, "text": self.text,
                "epistemic_state": self.epistemic_state.value,
                "evidence_doc_ids": list(self.evidence_doc_ids),
                "fragment_ids": list(self.fragment_ids),
                "technique_ids": list(self.technique_ids), "created_by": self.created_by}


@dataclass
class ClaimAssessment:
    claim_id: str
    grounded: bool                 # FACT requires evidence (§102)
    grounded_claim_ratio: float = 1.0
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"claim_id": self.claim_id, "grounded": self.grounded,
                "grounded_claim_ratio": self.grounded_claim_ratio, "notes": self.notes}


# ---------------------------------------------------------------------------
# Entities / knowledge graph
# ---------------------------------------------------------------------------

@dataclass
class EntityAlias:
    alias: str
    language: str = "en"
    source_doc_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EntityNode:
    entity_id: str = field(default_factory=lambda: _new_id("ent"))
    label: str = ""
    node_type: str = ""                 # Technology|Problem|Paper|Patent|Company|Person|... (§37)
    aliases: list[EntityAlias] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)
    source_doc_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"entity_id": self.entity_id, "label": self.label, "node_type": self.node_type,
                "aliases": [a.to_dict() for a in self.aliases], "properties": self.properties,
                "source_doc_ids": list(self.source_doc_ids)}


@dataclass
class RelationEdge:
    src: str                       # entity_id
    dst: str                       # entity_id
    relation: str                  # USES|SOLVES|CITES|... (§37)
    weight: float = 1.0
    source_doc_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"src": self.src, "dst": self.dst, "relation": self.relation,
                "weight": self.weight, "source_doc_ids": list(self.source_doc_ids)}


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------

@dataclass
class TopicObservation:
    topic: str
    period: str                    # e.g. "2026-08"
    frequency: int = 0
    source_diversity: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"topic": self.topic, "period": self.period, "frequency": self.frequency,
                "source_diversity": self.source_diversity, "metadata": self.metadata}


@dataclass
class Signal:
    signal_id: str = field(default_factory=lambda: _new_id("sig"))
    kind: str = ""                      # velocity|acceleration|burst|change_point|...
    topic: str = ""
    strength: float = 0.0          # normalized 0..1
    direction: str = "up"          # up|down|flat
    evidence_doc_ids: tuple[str, ...] = ()
    technique_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"signal_id": self.signal_id, "kind": self.kind, "topic": self.topic,
                "strength": self.strength, "direction": self.direction,
                "evidence_doc_ids": list(self.evidence_doc_ids),
                "technique_ids": list(self.technique_ids)}


@dataclass
class WeakSignal(Signal):
    """T099: low-frequency, high-potential early indicators."""
    lead_lag_hint: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({"lead_lag_hint": self.lead_lag_hint, "confidence": self.confidence})
        return d


# ---------------------------------------------------------------------------
# Gaps
# ---------------------------------------------------------------------------

@dataclass
class Gap:
    gap_id: str = field(default_factory=lambda: _new_id("gap"))
    kind: str = "research"         # research|limitation|contradiction|failure|white_space|...
    statement: str = ""
    evidence_doc_ids: tuple[str, ...] = ()
    technique_ids: tuple[str, ...] = ()
    epistemic_state: EpistemicState = EpistemicState.HYPOTHESIS

    def to_dict(self) -> dict[str, Any]:
        return {"gap_id": self.gap_id, "kind": self.kind, "statement": self.statement,
                "evidence_doc_ids": list(self.evidence_doc_ids),
                "technique_ids": list(self.technique_ids),
                "epistemic_state": self.epistemic_state.value}


@dataclass
class Contradiction(Gap):
    kind: str = "contradiction"
    doc_a: str = ""                # conflicting doc ids
    doc_b: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({"doc_a": self.doc_a, "doc_b": self.doc_b})
        return d


@dataclass
class Limitation(Gap):
    kind: str = "limitation"
    scope: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({"scope": self.scope})
        return d


@dataclass
class FailureCase(Gap):
    kind: str = "failure"
    failure_mode: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({"failure_mode": self.failure_mode})
        return d


@dataclass
class ResurrectionCandidate(Gap):
    """Evidence-backed candidate for reviving a previously blocked idea."""
    kind: str = "resurrection"
    dormant_since: str = ""
    unlock_enabler: str = ""
    historical_idea: str = ""
    historical_failure_reason: str = ""
    blocking_constraint: str = ""
    current_evidence: str = ""
    constraint_change: str = ""
    new_feasibility: str = ""
    resurrection_confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({
            "dormant_since": self.dormant_since,
            "unlock_enabler": self.unlock_enabler,
            "historical_idea": self.historical_idea,
            "historical_failure_reason": self.historical_failure_reason,
            "blocking_constraint": self.blocking_constraint,
            "current_evidence": self.current_evidence,
            "constraint_change": self.constraint_change,
            "new_feasibility": self.new_feasibility,
            "resurrection_confidence": self.resurrection_confidence,
        })
        return d


@dataclass
class WhiteSpaceCandidate(Gap):
    kind: str = "white_space"
    space_type: str = ""           # patent|research|market

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({"space_type": self.space_type})
        return d


# ---------------------------------------------------------------------------
# Hypotheses / invention
# ---------------------------------------------------------------------------

@dataclass
class Hypothesis:
    hypothesis_id: str = field(default_factory=lambda: _new_id("hyp"))
    statement: str = ""
    rationale: str = ""
    epistemic_state: EpistemicState = EpistemicState.HYPOTHESIS
    gap_ids: tuple[str, ...] = ()
    evidence_doc_ids: tuple[str, ...] = ()
    technique_ids: tuple[str, ...] = ()
    falsifiable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {"hypothesis_id": self.hypothesis_id, "statement": self.statement,
                "rationale": self.rationale, "epistemic_state": self.epistemic_state.value,
                "gap_ids": list(self.gap_ids), "evidence_doc_ids": list(self.evidence_doc_ids),
                "technique_ids": list(self.technique_ids), "falsifiable": self.falsifiable}


@dataclass
class InventionCandidate:
    candidate_id: str = field(default_factory=lambda: _new_id("cand"))
    title: str = ""
    description: str = ""
    mechanism: str = ""            # function→mechanism (T063)
    operators: tuple[str, ...] = ()  # technique ids that produced it
    hypothesis_id: str = ""
    epistemic_state: EpistemicState = EpistemicState.HYPOTHESIS
    origin: str = "NEW_IIE"        # LEGACY_CRIBA|NEW_IIE|EXTERNAL_ADAPTER (§144)

    def to_dict(self) -> dict[str, Any]:
        return {"candidate_id": self.candidate_id, "title": self.title,
                "description": self.description, "mechanism": self.mechanism,
                "operators": list(self.operators), "hypothesis_id": self.hypothesis_id,
                "epistemic_state": self.epistemic_state.value, "origin": self.origin}


# ---------------------------------------------------------------------------
# Prior art
# ---------------------------------------------------------------------------

@dataclass
class PriorArtQuery:
    candidate_id: str
    variants: list[QueryVariant] = field(default_factory=list)
    rounds: int = 0
    max_rounds: int = 3
    max_mutations: int = 3

    def to_dict(self) -> dict[str, Any]:
        return {"candidate_id": self.candidate_id,
                "variants": [v.to_dict() for v in self.variants],
                "rounds": self.rounds, "max_rounds": self.max_rounds,
                "max_mutations": self.max_mutations}


@dataclass
class PriorArtMatch:
    doc: EvidenceDocument
    similarity: float = 0.0        # 0..1
    match_kind: str = "literal"    # literal|synonym|semantic|classification|cross_domain
    overlapping_terms: tuple[str, ...] = ()
    scout: str = ""                # PatentScout|ScienceScout|CodeScout|...

    def to_dict(self) -> dict[str, Any]:
        return {"doc": self.doc.to_dict(), "similarity": self.similarity,
                "match_kind": self.match_kind, "overlapping_terms": list(self.overlapping_terms),
                "scout": self.scout}


@dataclass
class PriorArtAssessment:
    candidate_id: str
    verdict: str                   # KNOWN|NEAR_PRIOR_ART|PARTIAL_PRIOR_ART|UNRESOLVED|SURVIVED_SEARCH (§41)
    matches: list[PriorArtMatch] = field(default_factory=list)
    coverage_limitations: tuple[str, ...] = ()
    queries_executed: tuple[str, ...] = ()
    languages_searched: tuple[str, ...] = ("en",)
    classifications_searched: tuple[str, ...] = ()
    technique_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"candidate_id": self.candidate_id, "verdict": self.verdict,
                "matches": [m.to_dict() for m in self.matches],
                "coverage_limitations": list(self.coverage_limitations),
                "queries_executed": list(self.queries_executed),
                "languages_searched": list(self.languages_searched),
                "classifications_searched": list(self.classifications_searched),
                "technique_ids": list(self.technique_ids)}


# ---------------------------------------------------------------------------
# Assessments / scorecard
# ---------------------------------------------------------------------------

@dataclass
class NoveltyAssessment:
    global_novelty: float = 0.0
    local_novelty: float = 0.0
    temporal_novelty: float = 0.0
    structural_novelty: float = 0.0
    combinatorial_novelty: float = 0.0
    semantic_distance: float = 0.0
    prior_art_similarity: float = 1.0
    cluster_density: float = 0.0
    white_space_score: float = 0.0
    rationale: str = ""
    technique_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "global_novelty": self.global_novelty, "local_novelty": self.local_novelty,
            "temporal_novelty": self.temporal_novelty, "structural_novelty": self.structural_novelty,
            "combinatorial_novelty": self.combinatorial_novelty,
            "semantic_distance": self.semantic_distance,
            "prior_art_similarity": self.prior_art_similarity,
            "cluster_density": self.cluster_density, "white_space_score": self.white_space_score,
            "rationale": self.rationale, "technique_ids": list(self.technique_ids),
        }


@dataclass
class EvidenceAssessment:
    grounded_claim_ratio: float = 0.0
    multi_source_confirmation: int = 0
    source_diversity: int = 0
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"source_diversity": self.source_diversity}


@dataclass
class ConfidenceAssessment:
    confidence: float = 0.0
    epistemic_distribution: dict[str, int] = field(default_factory=dict)
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"confidence": self.confidence,
                "epistemic_distribution": self.epistemic_distribution,
                "rationale": self.rationale}


@dataclass
class FeasibilityAssessment:
    feasibility: float = 0.0
    blockers: tuple[str, ...] = ()
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"feasibility": self.feasibility, "blockers": list(self.blockers),
                "rationale": self.rationale}


@dataclass
class TRLAssessment:
    trl: int = 1                   # 1..9
    evidence: str = ""
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"trl": self.trl, "evidence": self.evidence, "rationale": self.rationale}


@dataclass
class PrototypeabilityAssessment:
    prototypeability: float = 0.0
    cost_to_test: float = 0.0      # 0..1 normalized (1 = expensive)
    time_to_test_days: int = 0
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"prototypeability": self.prototypeability, "cost_to_test": self.cost_to_test,
                "time_to_test_days": self.time_to_test_days, "rationale": self.rationale}


@dataclass
class CompetitionAssessment:
    saturation: float = 0.0
    competitive_density: float = 0.0
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PatentRiskAssessment:
    blocking_risk: float = 0.0
    relevant_patents: tuple[str, ...] = ()
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"blocking_risk": self.blocking_risk,
                "relevant_patents": list(self.relevant_patents), "rationale": self.rationale}


@dataclass
class OpportunityAssessment:
    opportunity: float = 0.0
    impact: float = 0.0
    time_to_market: float = 0.0
    regulatory_risk: float = 0.0
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScoreCard:
    """§44 SCORECARD V2 — additive, legacy score untouched."""
    candidate_id: str
    novelty: NoveltyAssessment | None = None
    evidence: EvidenceAssessment | None = None
    confidence: ConfidenceAssessment | None = None
    feasibility: FeasibilityAssessment | None = None
    trl: TRLAssessment | None = None
    prototypeability: PrototypeabilityAssessment | None = None
    competition: CompetitionAssessment | None = None
    patent_risk: PatentRiskAssessment | None = None
    opportunity: OpportunityAssessment | None = None
    growth: float = 0.0
    acceleration: float = 0.0
    underhype: float = 0.0
    timing: float = 0.0
    source_diversity: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"candidate_id": self.candidate_id}
        for name in ("novelty", "evidence", "confidence", "feasibility", "trl",
                     "prototypeability", "competition", "patent_risk", "opportunity"):
            obj = getattr(self, name)
            out[name] = obj.to_dict() if obj else None
        out.update(growth=self.growth, acceleration=self.acceleration,
                   underhype=self.underhype, timing=self.timing,
                   source_diversity=self.source_diversity)
        return out


@dataclass
class RankingResult:
    ranking: str                   # MOST_NOVEL|MOST_BUILDABLE|... (§45)
    items: list[tuple[str, float]] = field(default_factory=list)  # (candidate_id, score)

    def to_dict(self) -> dict[str, Any]:
        return {"ranking": self.ranking, "items": [list(i) for i in self.items]}


# ---------------------------------------------------------------------------
# Run / packet
# ---------------------------------------------------------------------------

@dataclass
class IntelligenceRun:
    run_id: str = field(default_factory=lambda: _new_id("run"))
    goal: str = ""
    intent: str = "discovery"
    preset: str = "BALANCED"
    started_at: str = field(default_factory=_now_iso)
    finished_at: str = ""
    status: str = "RUNNING"        # RUNNING|DONE|FAILED|DEGRADED
    techniques_used: tuple[str, ...] = ()
    request_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"run_id": self.run_id, "goal": self.goal, "intent": self.intent,
                "preset": self.preset, "started_at": self.started_at,
                "finished_at": self.finished_at, "status": self.status,
                "techniques_used": list(self.techniques_used),
                "request_count": self.request_count}


@dataclass
class IntelligencePacket:
    """§46: additive `packet["intelligence"]` — legacy clients ignore it."""
    run: IntelligenceRun = field(default_factory=IntelligenceRun)
    documents: list[EvidenceDocument] = field(default_factory=list)
    claims: list[Claim] = field(default_factory=list)
    entities: list[EntityNode] = field(default_factory=list)
    relations: list[RelationEdge] = field(default_factory=list)
    signals: list[Signal] = field(default_factory=list)
    gaps: list[Gap] = field(default_factory=list)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    candidates: list[InventionCandidate] = field(default_factory=list)
    prior_art: list[PriorArtAssessment] = field(default_factory=list)
    scorecards: list[ScoreCard] = field(default_factory=list)
    rankings: list[RankingResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run": self.run.to_dict(),
            "documents": [d.to_dict() for d in self.documents],
            "claims": [c.to_dict() for c in self.claims],
            "entities": [e.to_dict() for e in self.entities],
            "relations": [r.to_dict() for r in self.relations],
            "signals": [s.to_dict() for s in self.signals],
            "gaps": [g.to_dict() for g in self.gaps],
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "candidates": [c.to_dict() for c in self.candidates],
            "prior_art": [p.to_dict() for p in self.prior_art],
            "scorecards": [s.to_dict() for s in self.scorecards],
            "rankings": [r.to_dict() for r in self.rankings],
        }
