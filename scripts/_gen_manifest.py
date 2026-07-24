import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\PROYECTS\CRIBA")
OUT = ROOT / "dist" / "CRIBA-Blackforge-Portable-Windows-x64"

commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()

import PySide6, PyInstaller  # noqa: E402

catalog = ROOT / "imports/blackforge_v2/criba_blackforge_catalogo_final_debate20.json"
catalog_sha = hashlib.sha256(catalog.read_bytes()).hexdigest()

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

manifest = {
    "product": "CRIBA + BLACKFORGE",
    "version": "0.1.0",
    "commit": commit,
    "branch": branch,
    "date_utc": "2026-07-24",
    "build_system": "PyInstaller onedir (GUI windowed + CLI console, shared runtime via MERGE)",
    "python_version": sys.version.split()[0],
    "pyside6_version": PySide6.__version__,
    "packaging_tool": f"PyInstaller {PyInstaller.__version__}",
    "entrypoints": {
        "gui": "scripts/portable_entry_gui.py -> criba.gui:run (CRIBA-Blackforge.exe, windowed)",
        "cli": "scripts/portable_entry.py -> criba.cli:main (CRIBA-Blackforge-CLI.exe, console, UTF-8 forced)",
    },
    "executables": {
        "CRIBA-Blackforge.exe": {"subsystem": "windowed (2)", "sha256": sha(OUT / "CRIBA-Blackforge.exe")},
        "CRIBA-Blackforge-CLI.exe": {"subsystem": "console (3)", "sha256": sha(OUT / "CRIBA-Blackforge-CLI.exe")},
    },
    "included": [
        "CRIBA-Blackforge.exe (GUI, double-click)",
        "CRIBA-Blackforge-CLI.exe (CLI, automation)",
        "_internal/ (Python 3.11 runtime + PySide6/Qt6 + dependencies)",
        "_internal/data/ (CRIBA catalogs: currents, methods, schemas, themes, assets)",
        "_internal/imports/blackforge_v2/ (immutable BLACKFORGE catalog, 723 records)",
        "samples/query_example.txt",
        "FIRST_RUN_ES.md", "FIRST_RUN_EN.md", "THIRD_PARTY_NOTICES.md",
    ],
    "blackforge_catalog": {"records": 723, "sha256": catalog_sha},
    "tests": "213 passed (local pytest); mypy --strict rc=0 over 20 core source files (gui.py runtime-verified, excluded from strict typing)",
    "smoke_test": {
        "gui_exe_launches": True,
        "gui_from_path_with_spaces": True,
        "cli_activate": True,
        "cli_persistence_explain": True,
        "cli_database_flag": True,
        "utf8_accents_correct": True,
    },
    "limitations": [
        "AGENTIC layer is a future hook (NotImplementedError by design; LOCAL_MVP is the active adapter).",
        "GUI is runtime-verified (offscreen smoke + UI contract 11/11), not strictly typed.",
        "Sessions persist to %LOCALAPPDATA%/CRIBA-Blackforge/criba.sqlite3 by default (override with CLI --database).",
    ],
    "reproducibility": {
        "command": ".venv\\Scripts\\python.exe -m PyInstaller --noconfirm --clean CRIBA-Blackforge.spec",
        "script": "scripts/build-portable.ps1",
        "note": "Reproducible on Windows 11 x64 with the project .venv (Python 3.11.15) + PyInstaller 6.21.0 + PySide6 6.11.1.",
    },
}

(OUT / "BUILD_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print("BUILD_MANIFEST.json written")
print("GUI exe sha:", manifest["executables"]["CRIBA-Blackforge.exe"]["sha256"][:16])
print("catalog records:", manifest["blackforge_catalog"]["records"])
