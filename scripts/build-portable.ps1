param([string]$Python='C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe')
$root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$dataSpec=(Join-Path $root 'data') + ';data'
& $Python -m PyInstaller --noconfirm --clean --name CRIBA-Current-Engine --paths (Join-Path $root 'src') --add-data $dataSpec (Join-Path $root 'scripts\portable_entry.py')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
