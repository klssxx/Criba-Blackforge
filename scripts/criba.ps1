[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$uv = (Get-Command uv -CommandType Application -ErrorAction SilentlyContinue).Source
if (-not $uv) {
    throw 'uv not found. Install uv 0.11.28 and run "uv sync --all-extras --locked".'
}

Push-Location $root
try {
    if ($Arguments -and $Arguments.Count -gt 0) {
        & $uv run --locked --all-extras python -m criba.cli @Arguments
    }
    else {
        & $uv run --locked --all-extras python -m criba.cli gui
    }
    $exitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}
exit $exitCode
