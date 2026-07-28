from pathlib import Path
import os
import sys

PACKAGE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
DATA_ROOT = PACKAGE_ROOT / "data"
if getattr(sys, "frozen", False):
    # Portable executable: keep the SQLite store in a persistent, user-writable
    # location (the frozen bundle dir is ephemeral / read-only on some setups).
    _DB_BASE = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "CRIBA-Blackforge"
    DEFAULT_DB = _DB_BASE / "criba.sqlite3"
else:
    DEFAULT_DB = PACKAGE_ROOT / "artifacts" / "criba.sqlite3"
MAX_QUERY_CHARS = 20_000
SELECTOR_VERSION = "1.0.0"
CURRENT_CATALOG_VERSION = "1.0.0"
VALID_MODES = {"balanced", "strict", "creative", "adversarial", "minimal"}
VALID_DECISIONS = {"ADOPTAR", "AMPLIAR PRUEBA", "ABANDONAR", "ARCHIVAR PARA RECOMBINAR"}

# FASE 0 — alternativa C (ratificada por humano, 01_TAREA_ACTUAL.txt).
# Campo INDEPENDIENTE de recommended_status: la accion de siguiente paso del
# pipeline (que hacer despues), no el estado de la idea. Se anade de forma
# aditiva; recommended_status sigue restringido a VALID_DECISIONS.
VALID_PIPELINE_ACTIONS = {"PROTOTIPAR", "DIVERGIR"}

# HIPERMEGAPROMPT feature flags — all OFF by default (§16).
# Activate incrementally; existing behaviour is preserved when flags are False.
FEATURES: dict[str, bool] = {
    "context_layer_v2": False,
    "compound_personas": False,
    "ensemble_analysis": False,
    "six_stage_chain": False,
    "adversarial_self_reinforcement": False,
    "human_review_gates": False,
    "blackforge_extended_context": False,
    "deterministic_validation": False,
    "structured_logging": False,
    "quality_feedback_loop": False,
}
