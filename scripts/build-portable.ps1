# Build portable CRIBA + BLACKFORGE GUI via PyInstaller (onedir) from the spec.
# Uses the project-local .venv interpreter (self-contained, reproducible).
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$Python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) {
    Write-Error "Project .venv interpreter not found at: $Python"
    exit 1
}
$spec = Join-Path $root 'CRIBA-Blackforge.spec'
& $Python -m PyInstaller --noconfirm --clean $spec
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Portable GUI build complete: dist\CRIBA-Blackforge\CRIBA-Blackforge.exe"
