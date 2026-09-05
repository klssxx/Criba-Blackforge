import os
import sys
from pathlib import Path

PACKAGE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))


def _source_checkout_root() -> Path:
    """Repo root when running from a checkout (has pyproject.toml beside data)."""
    return Path(__file__).resolve().parents[2]


def _resolve_data_root() -> Path:
    """Locate the method/intelligence data in portable, checkout and wheel layouts."""
    frozen = getattr(sys, "_MEIPASS", None)
    if frozen:
        return Path(frozen) / "data"  # portable executable bundle
    source_root = _source_checkout_root()
    if (source_root / "pyproject.toml").is_file():
        return source_root / "data"  # source checkout / editable install
    try:
        # pip-installed wheel: data ships as a top-level namespace package.
        from importlib.util import find_spec

        spec = find_spec("data")
        if spec is not None and spec.submodule_search_locations:
            return Path(next(iter(spec.submodule_search_locations)))
    except Exception:
        pass
    return source_root / "data"


DATA_ROOT = _resolve_data_root()
_DB_BASE = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "CRIBA-Blackforge"
if getattr(sys, "frozen", False):
    # Portable executable: keep the SQLite store in a persistent, user-writable
    # location (the frozen bundle dir is ephemeral / read-only on some setups).
    DEFAULT_DB = _DB_BASE / "criba.sqlite3"
elif (Path(__file__).resolve().parents[2] / "pyproject.toml").is_file():
    DEFAULT_DB = PACKAGE_ROOT / "artifacts" / "criba.sqlite3"
else:
    # pip-installed: site-packages is not writable, keep state user-local.
    DEFAULT_DB = _DB_BASE / "criba.sqlite3"
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
    "ensemble_analysis": True,
    "six_stage_chain": True,
    "adversarial_self_reinforcement": True,
    "human_review_gates": True,
    "blackforge_extended_context": True,
    "deterministic_validation": True,
    "structured_logging": True,
    "quality_feedback_loop": True,
    "interprete_serendipia": False,
}
