# PROVENANCE — CRIBA + BLACKFORGE Portable v0.1.0

## Artifact
- File: `CRIBA-Blackforge-Portable-Windows-x64.zip`
- SHA-256: `bf0eef4ac374027017aba7bd38045a3e1f22772aed0e23c06abcd7e711d0599b`
- Size: 63,897,395 bytes (≈61 MB compressed, ≈139 MB extracted)
- ZIP integrity: `testzip` OK, 352 entries.

## Source
- Repository: `klssxx/Criba-Blackforge` (GitHub, PRIVATE).
- Branch: `main`
- Commit: `a86c1d5` (+ this session's reconciliation commits, see BUILD_DELTA).

## Build environment
- OS: Windows 11 x64.
- Interpreter: project `.venv` — CPython 3.11.15.
- Packaging: PyInstaller 6.21.0 (onedir).
- GUI toolkit: PySide6 / Qt 6.11.1.
- Command: `.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean CRIBA-Blackforge.spec`
  (wrapper: `scripts/build-portable.ps1`).

## Contents (two executables, one shared runtime)
- `CRIBA-Blackforge.exe` — GUI, windowed (PE subsystem 2). Double-click to open.
  SHA-256: `6ee3c32fa1eea27c...` (full hash in BUILD_MANIFEST.json).
- `CRIBA-Blackforge-CLI.exe` — CLI, console (PE subsystem 3), UTF-8 stdio forced.
- `_internal/` — Python runtime + PySide6/Qt6 + `data/` (CRIBA catalogs) +
  `imports/blackforge_v2/` (immutable BLACKFORGE catalog, 723 records,
  SHA-256 `1c698d540fbb22d6...`).
- `samples/query_example.txt`, `FIRST_RUN_ES.md`, `FIRST_RUN_EN.md`,
  `THIRD_PARTY_NOTICES.md`, `BUILD_MANIFEST.json`.

## Verification performed (real executables, not source)
- CLI `activate` on the bundled sample → valid packet (exit 0).
- CLI `activate` + `explain` → persistence round-trip verified.
- CLI `--database <win-path>` → writes to the requested DB (verified).
- GUI `.exe` → window launches and stays alive (offscreen), no traceback.
- GUI `.exe` from a path **with spaces** → launches, no crash.
- BLACKFORGE catalog (723 records) loads from the bundled runtime.
- Accented Spanish output renders correctly (UTF-8, no cp1252 garbling).
- Suite: 213 tests passed; `mypy --strict` rc=0 over 20 core files.

## Reproducibility
Rebuilding on the same interpreter + PyInstaller + PySide6 versions yields
functionally identical executables (verified: two clean builds produced
byte-size-identical exes). Exact byte-for-byte hash equality is not guaranteed
across machines due to PyInstaller/UPX and embedded timestamps.
