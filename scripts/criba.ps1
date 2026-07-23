param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments)
$python = 'C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Python portable no localizado. Define CRIBA_PYTHON o instala Python 3.10+.' }
$env:PYTHONPATH = (Join-Path $PSScriptRoot '..\src')
& $python -m criba.cli @Arguments
exit $LASTEXITCODE

