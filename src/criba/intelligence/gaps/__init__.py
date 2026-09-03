"""IIE gaps sector."""

from .limitations import LimitationExtractor, extract_limitations
from .research import ResearchGapExtractor, extract_research_gaps

__all__ = [
    "LimitationExtractor",
    "ResearchGapExtractor",
    "extract_limitations",
    "extract_research_gaps",
]
