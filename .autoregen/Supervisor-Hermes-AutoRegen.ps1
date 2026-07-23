[CmdletBinding()]
param(
    [string]$ProjectRoot = "",
    [string]$HermesCommand = "hermes",
    [string]$Provider = "",
    [string]$Model = "",
    [int]$MaxGenerations = 20,
    [int]$RestartDelaySeconds = 5
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = Split-Path -Parent $PSScriptRoot
}
if (-not (Test-Path -LiteralPath $ProjectRoot)) {
    throw "No existe el proyecto: $ProjectRoot"
}
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path

$StateRoot = Join-Path $ProjectRoot ".autoregen"
$LogRoot = Join-Path $StateRoot "logs"
$TaskPath = Join-Path $ProjectRoot "01_TAREA_ACTUAL.txt"
$ProtocolPath = Join-Path $StateRoot "AUTOREGEN_GLOBAL.txt"
$HandoffPath = Join-Path $ProjectRoot "HANDOFF.md"
$SessionStatePath = Join-Path $StateRoot "session_handoff.json"
$ResumePath = Join-Path $ProjectRoot "RESUME_NEXT_SESSION.txt"
$RequestPath = Join-Path $StateRoot "regeneration_request.json"
$CompletedPath = Join-Path $StateRoot "project_completed.json"
$HumanDecisionPath = Join-Path $StateRoot "human_decision_required.json"
$SupervisorStatePath = Join-Path $StateRoot "supervisor_state.json"

New-Item -ItemType Directory -Force -Path $StateRoot, $LogRoot | Out-Null

function Section([string]$Text) {
    Write-Host ""
    Write-Host ("=" * 76) -ForegroundColor DarkCyan
    Write-Host $Text -ForegroundColor Cyan
    Write-Host ("=" * 76) -ForegroundColor DarkCyan
}

function Hash-Text([string]$Text) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [Text.Encoding]::UTF8.GetBytes($Text)
        return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $sha.Dispose()
    }
}

function Project-Fingerprint([string]$Root) {
    $git = Get-Command git -ErrorAction SilentlyContinue
    if ($git -and (Test-Path -LiteralPath (Join-Path $Root ".git"))) {
        $status = (& git -C $Root status --porcelain=v1 --untracked-files=normal 2>$null) -join "`n"
        $diff = (& git -C $Root diff --no-ext-diff 2>$null) -join "`n"
        return Hash-Text ($status + "`n---DIFF---`n" + $diff)
    }

    $rows = [Collections.Generic.List[string]]::new()
    Get-ChildItem -LiteralPath $Root -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object {
            $_.FullName -notmatch "\\(\.git|__pycache__|node_modules|dist|build|logs)\\"
        } |
        Sort-Object FullName |
        ForEach-Object {
            $rel = [IO.Path]::GetRelativePath($Root, $_.FullName)
            $rows.Add("$rel|$($_.Length)|$($_.LastWriteTimeUtc.Ticks)")
        }
    return Hash-Text ($rows -join "`n")
}

function Has-Option([string]$HelpText, [string]$LongOption) {
    return $HelpText -match ("(?m)(^|\s)" + [regex]::Escape($LongOption) + "([,\s=]|$)")
}

function Test-SignalAtLineStart([string]$Text, [string]$Signal) {
    if ([string]::IsNullOrEmpty($Text)) {
        return $false
    }

    # Elimina secuencias ANSI y exige que la señal comience una línea.
    # Así, "NO corresponde CONTEXT_REGENERATION_REQUIRED" no cuenta.
    $clean = $Text -replace "`e\[[0-9;?]*[ -/]*[@-~]", ""
    $pattern = "(?m)^[\t ]*" + [regex]::Escape($Signal)
    return $clean -match $pattern
}

function Build-HermesInvocation(
    [string]$HermesPath,
    [string]$GlobalHelp,
    [string]$ChatHelp,
    [string]$Prompt
) {
    $args = [Collections.Generic.List[string]]::new()

    # Opciones globales: SIEMPRE antes del subcomando.
    if (-not [string]::IsNullOrWhiteSpace($Provider)) {
        if (Has-Option $GlobalHelp "--provider") {
            $args.Add("--provider")
            $args.Add($Provider)
        }
        else {
            throw "Tu Hermes no anuncia --provider como opción global."
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($Model)) {
        if ((Has-Option $GlobalHelp "--model") -or ($GlobalHelp -match "(?m)(^|\s)-m([,\s]|$)")) {
            $args.Add("--model")
            $args.Add($Model)
        }
        else {
            throw "Tu Hermes no anuncia --model/-m como opción global."
        }
    }
    if (Has-Option $GlobalHelp "--pass-session-id") {
        $args.Add("--pass-session-id")
    }

    $args.Add("chat")

    # Opciones de chat: SIEMPRE después de 'chat'.
    if (Has-Option $ChatHelp "--checkpoints") {
        $args.Add("--checkpoints")
    }

    # No usamos -Q. Algunas versiones lo tienen y otras no.
    # El supervisor necesita salida para detectar las señales.
    if (Has-Option $ChatHelp "--query") {
        $args.Add("--query")
        $args.Add($Prompt)
    }
    elseif ($ChatHelp -match "(?m)(^|\s)-q([,\s]|$)") {
        $args.Add("-q")
        $args.Add($Prompt)
    }
    else {
        throw "Tu versión no anuncia -q/--query en 'hermes chat --help'."
    }

    return ,$args.ToArray()
}

function Bootstrap([int]$Generation) {
    $hasPersistedState = (
        (Test-Path -LiteralPath $HandoffPath) -and
        (Test-Path -LiteralPath $SessionStatePath)
    )
    $hasResumeFile = Test-Path -LiteralPath $ResumePath

    $resumeInstruction = if ($hasPersistedState) {
        $resumeLine = if ($hasResumeFile) {
            "Lee también RESUME_NEXT_SESSION.txt."
        }
        else {
            "RESUME_NEXT_SESSION.txt no existe; continúa desde next_exact_action del estado JSON y HANDOFF.md."
        }
@"
Esta es una sesión limpia de continuación, generación $Generation.
Después de leer la tarea y el protocolo, lee HANDOFF.md y
.autoregen/session_handoff.json. $resumeLine
Verifica el estado real. No repitas fases VERIFIED. Continúa exactamente desde
next_exact_action.
"@
    }
    else {
@"
Esta es la primera sesión, generación $Generation. Empieza desde el primer paso
de la tarea y crea checkpoints verificables.
"@
    }

    return @"
Trabaja exclusivamente sobre:

$ProjectRoot

Lee completos desde disco, en este orden:

1. $TaskPath
2. $ProtocolPath

$resumeInstruction

La autorregeneración está SIEMPRE ACTIVA.
No uses --continue ni --resume.
No termines con un resumen ambiguo.

Antes de finalizar debes hacer exactamente una de estas tres cosas:

A) Si toda la tarea está terminada y verificada:
- escribir .autoregen/project_completed.json;
- terminar con PROJECT_COMPLETED.

B) Si necesitas contexto limpio:
- actualizar HANDOFF.md;
- escribir .autoregen/session_handoff.json;
- escribir RESUME_NEXT_SESSION.txt;
- escribir .autoregen/regeneration_request.json;
- terminar con CONTEXT_REGENERATION_REQUIRED.

C) Si existe una decisión humana realmente bloqueante:
- actualizar HANDOFF.md;
- escribir .autoregen/session_handoff.json;
- escribir .autoregen/human_decision_required.json;
- terminar con HUMAN_DECISION_REQUIRED o con la señal específica exigida por
  la tarea, por ejemplo BASELINE_DECISION_REQUIRED.

Después de emitir cualquiera de esas señales, no ejecutes más herramientas ni
añadas más texto.

Empieza ahora.
"@
}

if (-not (Test-Path -LiteralPath $TaskPath)) {
    throw "Falta $TaskPath"
}
if (-not (Test-Path -LiteralPath $ProtocolPath)) {
    throw "Falta $ProtocolPath"
}
$taskContent = Get-Content -LiteralPath $TaskPath -Raw
if ($taskContent -match "PEGA_AQUI_TU_PROMPT") {
    Start-Process notepad.exe -ArgumentList "`"$TaskPath`""
    throw "Pega primero la tarea en 01_TAREA_ACTUAL.txt."
}

$resolved = Get-Command $HermesCommand -ErrorAction SilentlyContinue
if (-not $resolved) {
    throw "No se encuentra '$HermesCommand'."
}
$HermesPath = $resolved.Source

# Descubrimiento real de la CLI instalada.
$globalHelp = (& $HermesPath --help 2>&1) -join "`n"
$chatHelp = (& $HermesPath chat --help 2>&1) -join "`n"
$version = (& $HermesPath --version 2>&1) -join " "

Section "HERMES · AUTORREGENERACIÓN SIEMPRE ACTIVA · V2"
Write-Host "Proyecto : $ProjectRoot"
Write-Host "Hermes   : $HermesPath"
Write-Host "Versión  : $version"
Write-Host "Tarea    : $TaskPath"
Write-Host "Logs     : $LogRoot"

# Prueba de construcción antes de iniciar una sesión.
$probe = Build-HermesInvocation $HermesPath $globalHelp $chatHelp "DEVUELVE SOLO: CLI_OK"
Section "COMPATIBILIDAD CLI"
Write-Host ("Comando detectado: hermes " + (($probe | ForEach-Object {
    if ($_ -eq "DEVUELVE SOLO: CLI_OK") { '"<prompt>"' } else { $_ }
}) -join " "))
Write-Host "No se usa -Q. --checkpoints solo se añade si chat lo soporta." -ForegroundColor Green

$previousFingerprint = Project-Fingerprint $ProjectRoot
$noProgressRegenerations = 0

for ($generation = 1; $generation -le $MaxGenerations; $generation++) {
    Section "SESIÓN LIMPIA $generation / $MaxGenerations"

    Remove-Item -LiteralPath $RequestPath -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $CompletedPath -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $HumanDecisionPath -Force -ErrorAction SilentlyContinue

    $prompt = Bootstrap $generation
    $args = Build-HermesInvocation $HermesPath $globalHelp $chatHelp $prompt

    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $logPath = Join-Path $LogRoot ("session-{0:00}-{1}.log" -f $generation, $stamp)

    [ordered]@{
        schema_version = "2.0.0"
        status = "running"
        generation = $generation
        project_root = $ProjectRoot
        hermes_version = $version
        invocation = "hermes " + (($args | ForEach-Object {
            if ($_ -eq $prompt) { "<bootstrap_prompt>" } else { $_ }
        }) -join " ")
        started_at = (Get-Date).ToString("o")
        log_path = $logPath
    } | ConvertTo-Json -Depth 5 |
        Set-Content -LiteralPath $SupervisorStatePath -Encoding utf8

    Push-Location $ProjectRoot
    try {
        & $HermesPath @args 2>&1 | Tee-Object -FilePath $logPath
        $exitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }

    $output = if (Test-Path -LiteralPath $logPath) {
        Get-Content -LiteralPath $logPath -Raw
    } else { "" }

    $newFingerprint = Project-Fingerprint $ProjectRoot
    $progress = $newFingerprint -ne $previousFingerprint
    $completed = (
        (Test-Path -LiteralPath $CompletedPath) -or
        (Test-SignalAtLineStart $output "PROJECT_COMPLETED")
    )
    $regenerate = (
        (Test-Path -LiteralPath $RequestPath) -or
        (Test-SignalAtLineStart $output "CONTEXT_REGENERATION_REQUIRED")
    )
    $humanDecision = (
        (Test-Path -LiteralPath $HumanDecisionPath) -or
        (Test-SignalAtLineStart $output "HUMAN_DECISION_REQUIRED") -or
        (Test-SignalAtLineStart $output "BASELINE_DECISION_REQUIRED")
    )

    [ordered]@{
        schema_version = "2.0.0"
        status = "finished"
        generation = $generation
        exit_code = $exitCode
        progress_detected = $progress
        completed_signal = $completed
        regeneration_signal = $regenerate
        human_decision_signal = $humanDecision
        finished_at = (Get-Date).ToString("o")
        log_path = $logPath
    } | ConvertTo-Json -Depth 5 |
        Set-Content -LiteralPath $SupervisorStatePath -Encoding utf8

    if ($completed) {
        Section "TAREA COMPLETADA"
        Write-Host "Hermes emitió PROJECT_COMPLETED." -ForegroundColor Green
        exit 0
    }

    if ($humanDecision) {
        $missing = @()
        foreach ($required in @($HandoffPath, $SessionStatePath)) {
            if (-not (Test-Path -LiteralPath $required)) {
                $missing += $required
            }
        }
        if ($missing.Count -gt 0) {
            throw "Decisión humana solicitada sin estado persistido completo:`n - $($missing -join "`n - ")"
        }

        Section "DECISIÓN HUMANA REQUERIDA"
        Write-Host "Hermes se ha detenido correctamente ante un bloqueo." -ForegroundColor Yellow
        Write-Host "No se exige RESUME_NEXT_SESSION.txt para este estado."
        Write-Host "Revisa HANDOFF.md y .autoregen\session_handoff.json."
        Write-Host "Añade tu decisión a 01_TAREA_ACTUAL.txt y vuelve a iniciar el supervisor."
        exit 10
    }

    if ($regenerate) {
        $missing = @()
        foreach ($required in @($HandoffPath, $SessionStatePath, $ResumePath)) {
            if (-not (Test-Path -LiteralPath $required)) {
                $missing += $required
            }
        }
        if ($missing.Count -gt 0) {
            throw "Regeneración solicitada sin handoff completo:`n - $($missing -join "`n - ")"
        }

        if ($progress) { $noProgressRegenerations = 0 }
        else { $noProgressRegenerations++ }

        if ($noProgressRegenerations -ge 2) {
            throw "Dos regeneraciones consecutivas sin progreso. Bucle bloqueado."
        }

        Write-Host "Handoff válido. Abriendo una sesión nueva..." -ForegroundColor Yellow
        $previousFingerprint = $newFingerprint
        Start-Sleep -Seconds $RestartDelaySeconds
        continue
    }

    Section "SESIÓN TERMINADA SIN SEÑAL"
    Write-Host "Código: $exitCode"
    Write-Host "Log: $logPath"
    if ($exitCode -eq 2) {
        Write-Host "Parece un problema de sintaxis CLI. Consulta COMPATIBILIDAD_CLI.txt." -ForegroundColor Red
    }
    throw "Hermes no emitió PROJECT_COMPLETED, CONTEXT_REGENERATION_REQUIRED ni una señal de decisión humana."
}

throw "Máximo de generaciones alcanzado."