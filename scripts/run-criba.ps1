<CmdletBinding()]
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
$defaultPython = Join-Path $root '.venv\Scripts\python.exe'

if ($env:CRIBA_PYTHON) {
    $python = $env:CRIBA_PYTHON
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw "CRIBA_PYTHON does not point to an executable: $python"
    }
}
elseif (Test-Path -LiteralPath $defaultPython -PathType Leaf) {
    $python = $defaultPython
}
else {
    $systemPython = Get-Command python -CommandType Application -ErrorAction SilentlyContinue
    if (-not $systemPython) {
        throw 'Python not found. Create the project environment with "uv sync --all-extras --locked", or set CRIBA_PYTHON to Python 3.10+.'
    }
    $python = $systemPython.Source
}

$src = Join-Path $root 'src'
$env:PYTHONPATH = if ($env:PYTHONPATH) { "$src;$env:PYTHONPATH" } else { $src }

# Forzar UTF-8 en stdio para que los acentos en español no se dañen en la consola.
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

if ($Arguments -and $Arguments.Count -gt 0) {
    & $python -m criba.cli @Arguments
}
else {
    & $python -m criba.cli gui
}
exit $LASTEXITCODE
