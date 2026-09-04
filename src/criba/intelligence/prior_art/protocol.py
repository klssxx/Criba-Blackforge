"""Bounded control protocol for the P10 adversarial prior-art pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..enums import PriorArtVerdict


class PriorArtStage(str, Enum):
    """The mandatory order of a prior-art challenge."""

    QUERY_LATTICE = "QUERY_LATTICE"
    LITERAL_SEARCH = "LITERAL_SEARCH"
    SYNONYM_SEARCH = "SYNONYM_SEARCH"
    SEMANTIC_SEARCH = "SEMANTIC_SEARCH"
    CLASSIFICATION_SEARCH = "CLASSIFICATION_SEARCH"
    MULTILINGUAL_SEARCH = "MULTILINGUAL_SEARCH"
    PATENT_SCOUT = "PATENT_SCOUT"
    SCIENCE_SCOUT = "SCIENCE_SCOUT"
    CODE_SCOUT = "CODE_SCOUT"
    PRODUCT_SCOUT = "PRODUCT_SCOUT"
    CROSS_DOMAIN_SCOUT = "CROSS_DOMAIN_SCOUT"
    SKEPTIC = "SKEPTIC"
    VERDICT = "VERDICT"


_PRIOR_ART_STAGES = tuple(PriorArtStage)
_ALLOWED_VERDICTS = tuple(verdict.value for verdict in PriorArtVerdict)


@dataclass(frozen=True)
class AdversarialSearchProtocol:
    """Immutable, bounded control plane; scouts and verdict logic remain separate."""

    candidate_id: str
    max_prior_art_rounds: int = 3
    max_mutations_per_candidate: int = 3

    def __post_init__(self) -> None:
        if not self.candidate_id.strip():
            raise ValueError("candidate_id must not be blank")
        if self.max_prior_art_rounds < 1:
            raise ValueError("max_prior_art_rounds must be at least 1")
        if self.max_mutations_per_candidate < 0:
            raise ValueError("max_mutations_per_candidate must be non-negative")

    @property
    def stages(self) -> tuple[PriorArtStage, ...]:
        return _PRIOR_ART_STAGES

    @property
    def allowed_verdicts(self) -> tuple[str, ...]:
        return _ALLOWED_VERDICTS

    def can_execute(self, *, rounds_completed: int, mutations_completed: int) -> bool:
        """Return whether another bounded search round may be scheduled."""

        if rounds_completed < 0 or mutations_completed < 0:
            raise ValueError("completed counts must be non-negative")
        return rounds_completed < self.max_prior_art_rounds

    def can_mutate(self, *, mutations_completed: int) -> bool:
        """Return whether a candidate mutation may be scheduled."""

        if mutations_completed < 0:
            raise ValueError("mutations_completed must be non-negative")
        return mutations_completed < self.max_mutations_per_candidate
