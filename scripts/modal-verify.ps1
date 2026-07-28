[CmdletBinding()]
param(
    [ValidateSet(
        "environment",
        "p2",
        "all",
        "p2_tests",
        "full_regression",
        "mypy_p2",
        "ruff_p2",
        "coverage_p2",
        "property_p2",
        "adversarial_p2",
        "mutation_p2",
        "scope_guard",
        "feature_flags",
        "determinism",
        "hy3_review"
    )]
    [string]$Action = "all",

    [string]$Hy3ReviewPath = "artifacts\hy3\P2_REVIEW.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Runner = Join-Path $ProjectRoot ".autoregen\cloud\modal_criba_runner.py"

# El runner contiene varios entrypoints.
# Modal necesita que se indique explícitamente cuál debe ejecutar.
$RunnerRef = "${Runner}::main"

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "No se encontró el intérprete Python: $Python"
}

if (-not (Test-Path -LiteralPath $Runner -PathType Leaf)) {
    throw "No se encontró el runner Modal: $Runner"
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONDONTWRITEBYTECODE = "1"

$ExitCode = 1

Push-Location $ProjectRoot

try {
    Write-Host "Proyecto: $ProjectRoot"
    Write-Host "Runner:   $RunnerRef"
    Write-Host "Acción:   $Action"
    Write-Host ""

    & $Python -m modal --version

    if ($LASTEXITCODE -ne 0) {
        throw "Modal no está disponible en la venv del proyecto."
    }

    $ArgsList = @(
        "-m",
        "modal",
        "run",
        $RunnerRef,
        "--action",
        $Action
    )

    if ([System.IO.Path]::IsPathRooted($Hy3ReviewPath)) {
        $ReviewFull = $Hy3ReviewPath
    }
    else {
        $ReviewFull = Join-Path $ProjectRoot $Hy3ReviewPath
    }

    if (Test-Path -LiteralPath $ReviewFull -PathType Leaf) {
        Write-Host "Revisión Hy3: $ReviewFull"

        $ArgsList += @(
            "--hy3-review-path",
            $ReviewFull
        )
    }
    else {
        Write-Host "Revisión Hy3 no encontrada; se ejecuta sin ella."
    }

    Write-Host ""
    Write-Host "Ejecutando Modal..."

    & $Python @ArgsList
    $ExitCode = $LASTEXITCODE
}
catch {
    Write-Error $_
    $ExitCode = 1
}
finally {
    Pop-Location
}

exit $ExitCode