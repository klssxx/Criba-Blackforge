"""IIE gaps sector."""

from .contradictions import ContradictionAnalyzer, analyze_contradictions
from .dormant import (
    DormantPaperAnalyzer,
    DormantPaperDetector,
    DormantPaperExtractor,
    detect_dormant_papers,
    analyze_dormant_papers,
    extract_dormant_papers,
    find_dormant_papers,
)
from .failures import FailureCaseExtractor, FailureMiner, extract_failures, mine_failures
from .limitations import LimitationExtractor, extract_limitations
from .patent_expiration import (
    PatentExpirationAnalyzer,
    PatentExpirationOpportunityExtractor,
    PatentExpirationEngine,
    analyze_patent_expirations,
    analyze_patent_expiration,
    extract_patent_expiration_opportunities,
    find_patent_expiration_opportunities,
)
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
    "DormantPaperAnalyzer",
    "DormantPaperDetector",
    "DormantPaperExtractor",
    "FailureCaseExtractor",
    "FailureMiner",
    "LimitationExtractor",
    "ResearchGapExtractor",
    "PatentExpirationAnalyzer",
    "PatentExpirationOpportunityExtractor",
    "PatentExpirationEngine",
    "WhiteSpaceAnalyzer",
    "WhiteSpaceExtractor",
    "WhiteSpaceEngine",
    "ResurrectionCandidateExtractor",
    "ResurrectionExtractor",
    "TechnologyResurrectionExtractor",
    "TechnologyResurrection",
    "detect_dormant_papers",
    "analyze_dormant_papers",
    "extract_dormant_papers",
    "find_dormant_papers",
    "extract_failures",
    "mine_failures",
    "extract_limitations",
    "extract_research_gaps",
    "analyze_contradictions",
    "analyze_patent_expirations",
    "analyze_patent_expiration",
    "extract_patent_expiration_opportunities",
    "find_patent_expiration_opportunities",
    "extract_resurrection_candidates",
    "find_resurrection_candidates",
    "extract_resurrection",
    "analyze_white_spaces",
    "analyze_white_space",
    "extract_white_spaces",
    "find_white_spaces",
]
