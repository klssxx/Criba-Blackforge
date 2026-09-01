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
    @{ Source = 'FIRST_RUN_ES.md'; Destination = 'FIRST_RUN_ES.md' },
    @{ Source = 'FIRST_RUN_EN.md'; Destination = 'FIRST_RUN_EN.md' },
    @{ Source = 'docs\LOCAL_MODELS.md'; Destination = 'LOCAL_MODELS.md' },
    @{ Source = 'THIRD_PARTY_NOTICES.md'; Destination = 'THIRD_PARTY_NOTICES.md' },
    @{ Source = 'LICENSE'; Destination = 'LICENSE' }
)
foreach ($document in $portableDocs) {
    Copy-Item -LiteralPath (Join-Path $root $document.Source) `
        -Destination (Join-Path $portable $document.Destination) -Force
}
Write-Host "Portable build complete:"
Write-Host "  dist\CRIBA-Blackforge\CRIBA.exe"
Write-Host "  dist\CRIBA-Blackforge\BLACKFORGE.exe"
Write-Host "  dist\CRIBA-Blackforge\CRIBA-CLI.exe"
Write-Host "  FIRST_RUN_ES.md / FIRST_RUN_EN.md / LOCAL_MODELS.md"
Write-Host "  THIRD_PARTY_NOTICES.md / LICENSE"
