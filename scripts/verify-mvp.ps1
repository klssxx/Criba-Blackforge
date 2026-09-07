# verify-mvp.ps1 — GATE reproducible (conditions 13-17 + causal verification)
# Run BEFORE: opening the GUI, rebuilding the portable, or declaring MVP done.
# May be executed from any directory.
$ErrorActionPreference = "Stop"
$ROOT = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
Push-Location $ROOT

$UV = (Get-Command uv -CommandType Application -ErrorAction SilentlyContinue).Source
if (-not $UV) {
    throw 'uv not found. Install uv 0.11.28 and run "uv sync --all-extras --locked".'
}

Write-Host "=== CRIBA MVP GATE ===" -ForegroundColor Cyan

# 1) Generate headless golden master (no PySide6) if missing or stale
Write-Host "[16] Generando artefacto headless versionado..." -ForegroundColor Yellow
& $UV run --locked --all-extras python -c @"
import sys, json, os
sys.path.insert(0, r'$ROOT\src')
import criba.engine as engine
q = '¿Cómo podemos generar ideas estructuralmente nuevas para controlar las acciones de agentes autónomos sin depender de una autoridad central permanente?'
p = engine.activate(q, 'auto', 'balanced', 4)
sample = {k: v for k, v in p.items() if k not in ('activation_id','timestamp')}
os.makedirs(r'$ROOT\verification', exist_ok=True)
with open(r'$ROOT\verification\mvp_output_sample.json','w',encoding='utf-8') as f: json.dump(sample, f, ensure_ascii=False, indent=2)
stable = json.loads(json.dumps(sample, ensure_ascii=False, sort_keys=True))
with open(r'$ROOT\verification\mvp_output_sample.normalized.json','w',encoding='utf-8') as f: json.dump(stable, f, ensure_ascii=False, indent=2)
print('golden master + sample written')
"@

# 2) Run the verification suite (gate)
Write-Host "[13-16 + causal] Ejecutando pruebas..." -ForegroundColor Yellow
& $UV run --locked --all-extras pytest `
  tests/test_packet_ideas_invariant.py `
  tests/test_genome_similarity_unknown.py `
  tests/test_packet_v1_regression.py `
  tests/test_mvp_golden_output.py `
  tests/test_causal_mechanism.py `
  -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "GATE FALLÓ — no abrir GUI ni reconstruir portable." -ForegroundColor Red
    Pop-Location
    exit 1
}

# 3) Full relevant suite
Write-Host "[full] Suite completa relevante..." -ForegroundColor Yellow
& $UV run --locked --all-extras pytest tests/ -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "Suite completa con fallos." -ForegroundColor Red
    Pop-Location
    exit 1
}

Write-Host "GATE VERDE — MVP listo para verificación de GUI." -ForegroundColor Green
Pop-Location
