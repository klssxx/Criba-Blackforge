# Build the separate CRIBA.exe + BLACKFORGE.exe apps and CRIBA-CLI.exe.
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
Write-Host "Portable build complete:"
Write-Host "  dist\CRIBA-Blackforge\CRIBA.exe"
Write-Host "  dist\CRIBA-Blackforge\BLACKFORGE.exe"
Write-Host "  dist\CRIBA-Blackforge\CRIBA-CLI.exe"
