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
$portable = Join-Path $root 'dist\CRIBA-Blackforge'
$portableDocs = @(
    'FIRST_RUN_ES.md',
    'FIRST_RUN_EN.md',
    'THIRD_PARTY_NOTICES.md',
    'LICENSE'
)
foreach ($document in $portableDocs) {
    Copy-Item -LiteralPath (Join-Path $root $document) `
        -Destination (Join-Path $portable $document) -Force
}
Write-Host "Portable build complete:"
Write-Host "  dist\CRIBA-Blackforge\CRIBA.exe"
Write-Host "  dist\CRIBA-Blackforge\BLACKFORGE.exe"
Write-Host "  dist\CRIBA-Blackforge\CRIBA-CLI.exe"
Write-Host "  FIRST_RUN_ES.md / FIRST_RUN_EN.md / THIRD_PARTY_NOTICES.md / LICENSE"
