from pathlib import Path
import sys

PACKAGE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
DATA_ROOT = PACKAGE_ROOT / "data"
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
