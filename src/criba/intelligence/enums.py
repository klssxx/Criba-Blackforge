"""IIE enums (P01-T03). Layer L1 — imports nothing from criba outside intelligence."""
from __future__ import annotations

from enum import Enum

__all__ = [
    "Preset", "RunStatus", "PriorArtVerdict", "TechniqueStatus", "Origin",
    "CostClass", "ModelClass", "ExecutionProfile", "SourceKind",
]


class Preset(str, Enum):
    """Research budget presets (blueprint §35)."""
    QUICK = "QUICK"
    BALANCED = "BALANCED"
    DEEP = "DEEP"
    EXHAUSTIVE = "EXHAUSTIVE"


class RunStatus(str, Enum):
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    DEGRADED = "DEGRADED"


class PriorArtVerdict(str, Enum):
    """§41 — SURVIVED_SEARCH only; PROVEN_NEW is forbidden."""
    KNOWN = "KNOWN"
    NEAR_PRIOR_ART = "NEAR_PRIOR_ART"
    PARTIAL_PRIOR_ART = "PARTIAL_PRIOR_ART"
    UNRESOLVED = "UNRESOLVED"
    SURVIVED_SEARCH = "SURVIVED_SEARCH"


class TechniqueStatus(str, Enum):
    """Addendum §85."""
    IMPLEMENTED = "IMPLEMENTED"
    IMPLEMENTED_OPTIONAL = "IMPLEMENTED_OPTIONAL"
    IMPLEMENTED_SHADOW = "IMPLEMENTED_SHADOW"
    DEGRADED = "DEGRADED"
    UNCONFIGURED = "UNCONFIGURED"
    PLANNED = "PLANNED"
    DISABLED = "DISABLED"
    BLOCKED_EXTERNAL = "BLOCKED_EXTERNAL"


class Origin(str, Enum):
    """Addendum §144 capability provenance."""
    LEGACY_CRIBA = "LEGACY_CRIBA"
    LEGACY_BLACKFORGE = "LEGACY_BLACKFORGE"
    LEGACY_SUPRA = "LEGACY_SUPRA"
    NEW_IIE = "NEW_IIE"
    EXTERNAL_ADAPTER = "EXTERNAL_ADAPTER"


class CostClass(str, Enum):
    """Addendum §125."""
    CHEAP_LOCAL = "CHEAP_LOCAL"
    LOCAL_COMPUTE = "LOCAL_COMPUTE"
    FREE_NETWORK = "FREE_NETWORK"
    AUTH_NETWORK = "AUTH_NETWORK"
    EXPENSIVE_NETWORK = "EXPENSIVE_NETWORK"
    MODEL_LIGHT = "MODEL_LIGHT"
    MODEL_HEAVY = "MODEL_HEAVY"


class ModelClass(str, Enum):
    """Z.ai routing classes (addendum §86)."""
    GLM_LOW = "GLM-5.3-low"
    GLM_HIGH = "GLM-5.3-high"
    GLM_MAX = "GLM-5.3-max"
    FLASH = "GLM-5.3-Flash"


class ExecutionProfile(str, Enum):
    """Addendum §118."""
    QUICK_DISCOVERY = "QUICK_DISCOVERY"
    TECHNOLOGY_RADAR = "TECHNOLOGY_RADAR"
    DEEP_PRIOR_ART = "DEEP_PRIOR_ART"
    GAP_DISCOVERY = "GAP_DISCOVERY"
    INVENTION_EXPLORATION = "INVENTION_EXPLORATION"
    OPPORTUNITY_ANALYSIS = "OPPORTUNITY_ANALYSIS"
    FULL_INNOVATION_INTELLIGENCE = "FULL_INNOVATION_INTELLIGENCE"


class SourceKind(str, Enum):
    SCIENCE = "science"
    PATENTS = "patents"
    FUNDING = "funding"
    TRIALS = "trials"
    CODE = "code"
    AI_ASSETS = "ai_assets"
    PRODUCTS = "products"
    TRENDS = "trends"
    COMMUNITIES = "communities"
    JOBS = "jobs"
    SUPPLY_CHAIN = "supply_chain"
    REGULATION = "regulation"
    STANDARDS = "standards"
    PROCUREMENT = "procurement"
    NEWS = "news"
    WEB = "web"
    RELEASES = "releases"
