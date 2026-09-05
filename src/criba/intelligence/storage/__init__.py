"""IIE storage layer (P02).

intelligence.sqlite3 — SEPARATE from criba.sqlite3 (blueprint §29).
Never touch legacy storage. Migrations are additive & versioned.
"""
from .store import IntelligenceStore, DB_VERSION

__all__ = ["IntelligenceStore", "DB_VERSION"]
