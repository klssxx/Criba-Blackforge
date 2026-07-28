[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

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
# No subcommand -> launch the GUI (canonical Windows desktop app). Any explicit
# arguments are forwarded verbatim to the full CLI (list-currents, gui, etc.).
if ($Arguments -and $Arguments.Count -gt 0) {
    & $python -m criba.cli @Arguments
}
else {
    & $python -m criba.cli gui
}
exit $LASTEXITCODE
