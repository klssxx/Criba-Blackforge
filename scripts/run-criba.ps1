<CmdletBinding()>
<param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

<#
  Launcher canónico de CRIBA + BLACKFORGE (Windows 11).

  - Resuelve la raíz del proyecto de forma robusta (no depende de C:\Windows\System32).
  - Usa la venv del proyecto (o CRIBA_PYTHON si está definido).
  - Sin subcomando -> lanza la GUI de escritorio (ruta canónica: CribaMainWindow).
  - Cualquier argumento se reenvía al CLI (criba gui, criba blackforge --help, etc.).
  - Conserva el exit code del proceso hijo.
#>
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$uv = (Get-Command uv -CommandType Application -ErrorAction SilentlyContinue).Source
if (-not $uv) {
    throw 'uv not found. Install uv 0.11.28 and run "uv sync --all-extras --locked".'
}

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

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
