[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot,

    [ValidateSet("P2")]
    [string]$Phase = "P2",

    [ValidateSet("audit","improve")]
    [string]$HermesMode = "audit"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path $ProjectRoot).Path
$ModalWrapper = Join-Path $ProjectRoot "scripts\modal-verify.ps1"
$HermesWrapper = Join-Path $ProjectRoot "scripts\start-hermes-hy3.ps1"
$ReviewPath = Join-Path $ProjectRoot "artifacts\hy3\P2_REVIEW.json"

Write-Host "=== 1/3 Modal deterministic gates ==="
& pwsh -ExecutionPolicy Bypass -File $ModalWrapper -Action all
$ModalCode = $LASTEXITCODE

Write-Host "=== 2/3 Hermes + Hy3 semantic review ==="
& pwsh -ExecutionPolicy Bypass -File $HermesWrapper -ProjectRoot $ProjectRoot -Mode $HermesMode
$HermesCode = $LASTEXITCODE

if (-not (Test-Path -LiteralPath $ReviewPath)) {
    throw "Hermes no produjo el contrato requerido: $ReviewPath"
}

Write-Host "=== 3/3 Modal validates Hy3 review and reruns P2 gates ==="
& pwsh -ExecutionPolicy Bypass -File $ModalWrapper -Action p2 -Hy3ReviewPath $ReviewPath
$FinalCode = $LASTEXITCODE

if ($ModalCode -ne 0 -or $HermesCode -ne 0 -or $FinalCode -ne 0) {
    exit 1
}
exit 0
