[CmdletBinding()]
param(
    [string]$ProjectRoot = "E:\PROYECTS\CRIBA",
    [string]$PackageZip = (Join-Path $PSScriptRoot "CRIBA_BLACKFORGE_V2_IMPLEMENTACION_COMPLETA.zip"),
    [string]$HermesCommand = "hermes",
    [string]$Provider = "nous",
    [string]$Model = "hy3:free",
    [int]$MaxGenerations = 12,
    [int]$MaxUnmarkedRestarts = 2,
    [int]$RestartDelaySeconds = 8,
    [switch]$SkipPackageInstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Section {
    param([string]$Text)
    Write-Host ""
    Write-Host ("=" * 78) -ForegroundColor DarkCyan
    Write-Host $Text -ForegroundColor Cyan
    Write-Host ("=" * 78) -ForegroundColor DarkCyan
}

function Resolve-Executable {
    param([string]$Command)
    $resolved = Get-Command $Command -ErrorAction SilentlyContinue
    if (-not $resolved) {
        throw "No se encuentra '$Command'. Abre otra terminal tras instalar Hermes o indica -HermesCommand."
    }
    return $resolved.Source
}

function Get-TextSha256 {
    param([string]$Text)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $sha.Dispose()
    }
}

function Get-RepositoryFingerprint {
    param([string]$Root)

    $git = Get-Command git -ErrorAction SilentlyContinue
    if ($git -and (Test-Path (Join-Path $Root ".git"))) {
        $status = (& git -C $Root status --porcelain=v1 --untracked-files=normal 2>$null) -join "`n"
        $diff = (& git -C $Root diff --no-ext-diff --binary 2>$null) -join "`n"
        return Get-TextSha256 ($status + "`n---DIFF---`n" + $diff)
    }

    $roots = @("src", "tests", "scripts", "docs", "HANDOFF.md", "RESUME_NEXT_SESSION.txt")
    $lines = [System.Collections.Generic.List[string]]::new()

    foreach ($relative in $roots) {
        $path = Join-Path $Root $relative
        if (-not (Test-Path $path)) { continue }

        if ((Get-Item $path).PSIsContainer) {
            Get-ChildItem $path -Recurse -File -ErrorAction SilentlyContinue |
                Where-Object {
                    $_.FullName -notmatch "\\(\.git|__pycache__|logs|dist|build|imports)\\"
                } |
                Sort-Object FullName |
                ForEach-Object {
                    $rel = $_.FullName.Substring($Root.Length).TrimStart("\", "/")
                    $lines.Add("$rel|$($_.Length)|$($_.LastWriteTimeUtc.Ticks)")
                }
        }
        else {
            $item = Get-Item $path
            $rel = $item.FullName.Substring($Root.Length).TrimStart("\", "/")
            $lines.Add("$rel|$($item.Length)|$($item.LastWriteTimeUtc.Ticks)")
        }
    }

    return Get-TextSha256 ($lines -join "`n")
}

function Test-RequiredAssets {
    param([string]$Root)

    $required = @(
        "HIPER_MEGAPROMPT_CRIBA_BLACKFORGE_V2.txt",
        ".criba\AUTOSUPERVISION_PROMPT.txt",
        "imports\blackforge_v2\criba_blackforge_catalogo_final_debate20.json",
        "imports\blackforge_v2\criba_blackforge_politicas_v2.json",
        "imports\blackforge_v2\causal_engine.py",
        "imports\blackforge_v2\test_causal_engine.py"
    )

    $missing = @()
    foreach ($relative in $required) {
        if (-not (Test-Path (Join-Path $Root $relative))) {
            $missing += $relative
        }
    }

    if ($missing.Count -gt 0) {
        throw "Faltan assets obligatorios:`n - $($missing -join "`n - ")"
    }
}

function Test-RegenerationArtifacts {
    param([string]$Root)

    $required = @(
        "HANDOFF.md",
        ".criba\session_handoff.json",
        "RESUME_NEXT_SESSION.txt"
    )
    $missing = @()
    foreach ($relative in $required) {
        if (-not (Test-Path (Join-Path $Root $relative))) {
            $missing += $relative
        }
    }
    return $missing
}

function New-BootstrapPrompt {
    param(
        [string]$Root,
        [int]$Generation
    )

    $handoff = Join-Path $Root "HANDOFF.md"
    $state = Join-Path $Root ".criba\session_handoff.json"
    $resume = Join-Path $Root "RESUME_NEXT_SESSION.txt"

    $continuation = if (
        (Test-Path $handoff) -and
        (Test-Path $state) -and
        (Test-Path $resume)
    ) {
        @"
Esta es la generación limpia número $Generation. Existe un handoff anterior.
Después de leer los dos prompts principales, lee HANDOFF.md,
.criba/session_handoff.json y RESUME_NEXT_SESSION.txt. Verifica desde archivos
y pruebas la última fase, no repitas fases VERIFIED y continúa desde la próxima
acción exacta.
"@
    }
    else {
        @"
Esta es la primera generación. No existe un handoff completo previo. Empieza por
la FASE 0 del hiper-megaprompt: inspección, baseline, checkpoint e integración
incremental.
"@
    }

    return @"
Trabaja exclusivamente sobre: $Root

Lee desde disco, completos y en este orden:
1. $Root\HIPER_MEGAPROMPT_CRIBA_BLACKFORGE_V2.txt
2. $Root\.criba\AUTOSUPERVISION_PROMPT.txt

$continuation

Los archivos de datos están en:
$Root\imports\blackforge_v2

No pidas que se pegue su contenido en el chat. Inspecciónalos desde disco.
No uses --continue ni --resume. Esta sesión es deliberadamente limpia.
No alteres CRIBA normal antes de ejecutar el baseline.
No avances a una fase si su gate anterior no está verde.

Antes de terminar esta ejecución debes hacer exactamente una de estas dos cosas:

A) Si todos los criterios finales están realmente verificados:
- escribir .criba/project_completed.json;
- terminar con PROJECT_COMPLETED.

B) Si necesitas una sesión nueva por saturación o degradación:
- actualizar HANDOFF.md;
- escribir .criba/session_handoff.json;
- escribir RESUME_NEXT_SESSION.txt;
- escribir .criba/regeneration_request.json;
- terminar con CONTEXT_REGENERATION_REQUIRED.

No termines con un resumen ambiguo. Empieza ahora.
"@
}

Write-Section "SUPERVISOR HERMES · CRIBA / BLACKFORGE"

if (-not (Test-Path $ProjectRoot)) {
    throw "La ruta del proyecto no existe: $ProjectRoot"
}

$ProjectRoot = (Resolve-Path $ProjectRoot).Path
$HermesPath = Resolve-Executable $HermesCommand

Write-Host "Proyecto : $ProjectRoot"
Write-Host "Hermes   : $HermesPath"
Write-Host "Proveedor: $Provider"
Write-Host "Modelo   : $Model"

$cribaState = Join-Path $ProjectRoot ".criba"
$logRoot = Join-Path $cribaState "supervisor_logs"
New-Item -ItemType Directory -Force -Path $cribaState, $logRoot | Out-Null

if (-not $SkipPackageInstall) {
    Write-Section "INSTALANDO PAQUETE"
    if (-not (Test-Path $PackageZip)) {
        throw "No se encuentra el ZIP: $PackageZip"
    }
    Expand-Archive -LiteralPath $PackageZip -DestinationPath $ProjectRoot -Force
    Write-Host "Paquete extraído sin tocar src/tests existentes salvo archivos homónimos del ZIP."
}

$autoPromptSource = Join-Path $PSScriptRoot "AUTOSUPERVISION_PROMPT.txt"
$autoPromptTarget = Join-Path $cribaState "AUTOSUPERVISION_PROMPT.txt"
if (-not (Test-Path $autoPromptSource)) {
    throw "Falta AUTOSUPERVISION_PROMPT.txt junto al supervisor."
}
Copy-Item -LiteralPath $autoPromptSource -Destination $autoPromptTarget -Force

Test-RequiredAssets $ProjectRoot

$version = (& $HermesPath --version 2>&1) -join " "
Write-Host "Versión Hermes: $version"

$supervisorStatePath = Join-Path $cribaState "supervisor_state.json"
$regenerationRequest = Join-Path $cribaState "regeneration_request.json"
$completedSignal = Join-Path $cribaState "project_completed.json"

$previousFingerprint = Get-RepositoryFingerprint $ProjectRoot
$noProgressRegenerations = 0
$unmarkedRestarts = 0

for ($generation = 1; $generation -le $MaxGenerations; $generation++) {
    Write-Section "GENERACIÓN LIMPIA $generation / $MaxGenerations"

    Remove-Item $regenerationRequest -Force -ErrorAction SilentlyContinue
    Remove-Item $completedSignal -Force -ErrorAction SilentlyContinue

    $bootstrap = New-BootstrapPrompt -Root $ProjectRoot -Generation $generation
    $promptPath = Join-Path $logRoot ("bootstrap-generation-{0:00}.txt" -f $generation)
    $bootstrap | Set-Content -LiteralPath $promptPath -Encoding utf8

    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $logPath = Join-Path $logRoot ("generation-{0:00}-{1}.log" -f $generation, $timestamp)

    $state = [ordered]@{
        schema_version = "1.0.0"
        status = "running"
        generation = $generation
        max_generations = $MaxGenerations
        project_root = $ProjectRoot
        provider = $Provider
        model = $Model
        started_at = (Get-Date).ToString("o")
        log_path = $logPath
        bootstrap_path = $promptPath
    }
    $state | ConvertTo-Json -Depth 6 |
        Set-Content -LiteralPath $supervisorStatePath -Encoding utf8

    $arguments = @(
        "-Q",
        "--checkpoints",
        "--pass-session-id",
        "chat"
    )
    if ($Provider) {
        $arguments += @("--provider", $Provider)
    }
    if ($Model) {
        $arguments += @("--model", $Model)
    }
    $arguments += @("-q", $bootstrap)

    Push-Location $ProjectRoot
    try {
        Write-Host "Iniciando Hermes. La salida se guarda en:"
        Write-Host $logPath -ForegroundColor DarkGray

        & $HermesPath @arguments 2>&1 |
            Tee-Object -FilePath $logPath

        $exitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }

    $output = if (Test-Path $logPath) {
        Get-Content -LiteralPath $logPath -Raw -ErrorAction SilentlyContinue
    }
    else {
        ""
    }

    $newFingerprint = Get-RepositoryFingerprint $ProjectRoot
    $progressMade = $newFingerprint -ne $previousFingerprint

    $completed = (
        (Test-Path $completedSignal) -or
        ($output -match "(?m)^\s*PROJECT_COMPLETED\s*$")
    )
    $regenerate = (
        (Test-Path $regenerationRequest) -or
        ($output -match "CONTEXT_REGENERATION_REQUIRED")
    )

    $state.status = "finished"
    $state.finished_at = (Get-Date).ToString("o")
    $state.exit_code = $exitCode
    $state.progress_detected = $progressMade
    $state.completed_signal = $completed
    $state.regeneration_signal = $regenerate
    $state | ConvertTo-Json -Depth 6 |
        Set-Content -LiteralPath $supervisorStatePath -Encoding utf8

    if ($completed) {
        Write-Section "PROYECTO COMPLETADO"
        Write-Host "Hermes emitió PROJECT_COMPLETED y dejó el estado persistido." -ForegroundColor Green
        Write-Host "Revisa HANDOFF.md y ejecuta scripts\verify-all.ps1 manualmente antes de publicar."
        exit 0
    }

    if ($regenerate) {
        $missingHandoff = Test-RegenerationArtifacts $ProjectRoot
        if ($missingHandoff.Count -gt 0) {
            Write-Section "REGENERACIÓN BLOQUEADA"
            Write-Error (
                "Hermes pidió una sesión nueva, pero faltan artefactos de handoff:`n - " +
                ($missingHandoff -join "`n - ")
            )
            exit 20
        }

        if ($progressMade) {
            $noProgressRegenerations = 0
        }
        else {
            $noProgressRegenerations++
        }

        if ($noProgressRegenerations -ge 2) {
            Write-Section "BUCLE SIN PROGRESO DETECTADO"
            Write-Error "Dos regeneraciones consecutivas sin cambios verificables. Se detiene para evitar un bucle."
            exit 21
        }

        Write-Host "Handoff válido. Se abrirá una sesión realmente limpia." -ForegroundColor Yellow
        $previousFingerprint = $newFingerprint
        Start-Sleep -Seconds $RestartDelaySeconds
        continue
    }

    if ($exitCode -ne 0) {
        Write-Warning "Hermes terminó con código $exitCode y sin señal estructurada."
    }
    else {
        Write-Warning "Hermes terminó sin PROJECT_COMPLETED ni CONTEXT_REGENERATION_REQUIRED."
    }

    $unmarkedRestarts++
    if ($unmarkedRestarts -gt $MaxUnmarkedRestarts) {
        Write-Section "LÍMITE DE REINICIOS SIN MARCADOR"
        Write-Error "Se alcanzó el límite. Revisa el último log: $logPath"
        exit 22
    }

    $fallbackResume = @"
La sesión anterior terminó sin marcador estructurado.

Trabaja sobre $ProjectRoot.
Lee el hiper-megaprompt, el protocolo de autosupervisión y HANDOFF.md si existe.
Inspecciona el último log:
$logPath

No asumas que la fase estaba terminada. Verifica el estado real desde archivos,
git diff y tests. Actualiza HANDOFF.md y continúa desde la primera acción no
verificada. Al terminar, emite PROJECT_COMPLETED o
CONTEXT_REGENERATION_REQUIRED con todos sus artefactos.
"@
    $fallbackResume |
        Set-Content -LiteralPath (Join-Path $ProjectRoot "RESUME_NEXT_SESSION.txt") -Encoding utf8

    $previousFingerprint = $newFingerprint
    Start-Sleep -Seconds $RestartDelaySeconds
}

Write-Section "MÁXIMO DE GENERACIONES ALCANZADO"
Write-Error "Se alcanzaron $MaxGenerations sesiones sin PROJECT_COMPLETED. Revisa $logRoot y HANDOFF.md."
exit 23