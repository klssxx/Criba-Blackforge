# Environment Verification Script — CRIBA Toolchain
# Run: powershell -ExecutionPolicy Bypass -File scripts/verify-dev-environment.ps1

# Requires: PowerShell, winget, git, uv, python

Write-Host "=== CRIBA Development Toolchain Verification ===" -ForegroundColor Cyan

# --- Tool availability ---
$tools = @(
    "git", "gh", "python", "uv", "node", "pnpm", "docker", "docker-compose",
    "rg", "fd", "jq", "ruff", "bandit", "semgrep", "gitleaks",
    "trivy", "osv-scanner", "syft", "grype", "pip-audit", "pre-commit"
)

Write-Host "`n--- Tool availability ---" -ForegroundColor Yellow
foreach ($tool in $tools) {
    $found = $false
    try {
        $path = (Get-Command $tool -ErrorAction SilentlyContinue).Source
        if ($path) {
            $ver = & $tool --version 2>&1 | Select-Object -First 1
            Write-Host "  [OK] $tool : $ver" -ForegroundColor Green
            $found = $true
        }
    } catch {}
    if (-not $found) {
        Write-Host "  [MISSING] $tool" -ForegroundColor Red
    }
}

# --- Project roots ---
$cribaRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$supraRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\SUPRA")).Path
$projects = @(
    @{name="CRIBA"; path=$cribaRoot},
    @{name="SUPRA"; path=$supraRoot}
)
if ($env:THEKEY_ROOT -and (Test-Path $env:THEKEY_ROOT)) {
    $projects += @{name="THEKEY"; path=(Resolve-Path $env:THEKEY_ROOT).Path}
}

Write-Host "`n--- Project directories ---" -ForegroundColor Yellow
foreach ($p in $projects) {
    if (Test-Path $p.path) {
        $git = (Get-Content -Path "$($p.path)/.git/HEAD" -ErrorAction SilentlyContinue)
        Write-Host "  [OK] $($p.name) : $($p.path)" -ForegroundColor Green
        if ($git) { Write-Host "    git ref: $git" }
    } else {
        Write-Host "  [MISSING] $($p.name) : $($p.path)" -ForegroundColor Red
    }
}

# --- Python environments ---
Write-Host "`n--- Python environments ---" -ForegroundColor Yellow
foreach ($p in $projects) {
    $venv = "$($p.path)/.venv"
    if (Test-Path $venv) {
        Write-Host "  [OK] $($p.name) venv exists" -ForegroundColor Green
    } else {
        Write-Host "  [MISSING] $($p.name) venv" -ForegroundColor Yellow
    }
}

# --- Pre-commit configs ---
Write-Host "`n--- Pre-commit configs ---" -ForegroundColor Yellow
foreach ($p in $projects) {
    $f = "$($p.path)/.pre-commit-config.yaml"
    if (Test-Path $f) {
        Write-Host "  [OK] $($p.name): .pre-commit-config.yaml" -ForegroundColor Green
    } else {
        Write-Host "  [MISSING] $($p.name): .pre-commit-config.yaml" -ForegroundColor Yellow
    }
}

# --- Secret scan ---
Write-Host "`n--- Secret scan (gitleaks) ---" -ForegroundColor Yellow
try {
    & gitleaks detect --source $cribaRoot --verbose 2>&1 | Select-Object -Last 3
    Write-Host "  CRIBA: gitleaks completed" -ForegroundColor Green
} catch {
    Write-Host "  CRIBA: gitleaks failed" -ForegroundColor Red
}

Write-Host "`n=== Verification complete ===" -ForegroundColor Cyan
