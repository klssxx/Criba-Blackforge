"""IIE gaps sector."""

from .contradictions import ContradictionAnalyzer, analyze_contradictions
from .failures import FailureCaseExtractor, FailureMiner, extract_failures, mine_failures
from .limitations import LimitationExtractor, extract_limitations
from .research import ResearchGapExtractor, extract_research_gaps
from .resurrection import (
    ResurrectionCandidateExtractor,
    ResurrectionExtractor,
    TechnologyResurrectionExtractor,
    TechnologyResurrection,
    extract_resurrection_candidates,
    find_resurrection_candidates,
    extract_resurrection,
)
from .white_space import (
    WhiteSpaceAnalyzer,
    WhiteSpaceExtractor,
    WhiteSpaceEngine,
    analyze_white_spaces,
    analyze_white_space,
    extract_white_spaces,
    find_white_spaces,
)

__all__ = [
    "ContradictionAnalyzer",
    "FailureCaseExtractor",
    "FailureMiner",
    "LimitationExtractor",
    "ResearchGapExtractor",
    "extract_failures",
    "mine_failures",
    "extract_limitations",
    "extract_research_gaps",
    "extract_resurrection_candidates",
    "find_resurrection_candidates",
    "extract_resurrection",
    "ResurrectionCandidateExtractor",
    "ResurrectionExtractor",
    "TechnologyResurrectionExtractor",
    "TechnologyResurrection",
    "WhiteSpaceAnalyzer",
    "WhiteSpaceExtractor",
    "WhiteSpaceEngine",
    "analyze_white_spaces",
    "analyze_white_space",
    "extract_white_spaces",
    "find_white_spaces",
    "analyze_contradictions",
]
