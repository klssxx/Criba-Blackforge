"""IIE gaps sector."""

from .contradictions import ContradictionAnalyzer, analyze_contradictions
from .failures import FailureCaseExtractor, FailureMiner, extract_failures, mine_failures
from .limitations import LimitationExtractor, extract_limitations
from .research import ResearchGapExtractor, extract_research_gaps

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
    "analyze_contradictions",
]
