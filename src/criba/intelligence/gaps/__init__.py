"""IIE gaps sector."""

from .contradictions import ContradictionAnalyzer, analyze_contradictions
from .limitations import LimitationExtractor, extract_limitations
from .research import ResearchGapExtractor, extract_research_gaps

__all__ = [
    "ContradictionAnalyzer",
    "LimitationExtractor",
    "ResearchGapExtractor",
    "extract_limitations",
    "extract_research_gaps",
    "analyze_contradictions",
]
