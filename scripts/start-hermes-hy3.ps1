[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot,

    [ValidateSet("audit","improve")]
    [string]$Mode = "audit"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path $ProjectRoot).Path
$PromptPath = Join-Path $ProjectRoot "docs\prompts\HERMES_HY3_P2_ORCHESTRATOR.md"

if (-not (Get-Command hermes -ErrorAction SilentlyContinue)) {
    throw "No se encontró el comando hermes."
}
if (-not (Test-Path -LiteralPath $PromptPath)) {
    throw "No se encontró $PromptPath"
}

$Prompt = Get-Content -Raw -LiteralPath $PromptPath
$Prompt += "`n`nMODO_SOLICITADO=$Mode`nPROJECT_ROOT=$ProjectRoot"

Push-Location $ProjectRoot
try {
    hermes chat `
        --provider openrouter `
        --model "tencent/hy3:free" `
        --skills "modal-criba-orchestrator" `
        --query $Prompt
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
