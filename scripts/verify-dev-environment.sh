# Verify Development Environment — CRIBA Toolchain
# Run: ./scripts/verify-dev-environment.sh
# Requires: bash, git, uv, python, winget tools

set -euo pipefail

echo "=== CRIBA Development Toolchain Verification ==="

# --- Tool availability (system PATH) ---
echo ""
echo "--- Tool availability (system PATH) ---"
TOOLS_SYSTEM="git gh python uv node pnpm docker docker-compose rg fd jq gitleaks trivy osv-scanner syft grype"
for tool in $TOOLS_SYSTEM; do
    if command -v "$tool" >/dev/null 2>&1; then
        ver=$("$tool" --version 2>&1 | head -1)
        echo "  [OK] $tool : $ver"
    else
        echo "  [MISSING] $tool"
    fi
done

# --- Project roots ---
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
CRIBA_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
SUPRA_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../../SUPRA" && pwd)
THEKEY_ROOT=${THEKEY_ROOT:-}
PROJECT_ROOTS=("$CRIBA_ROOT" "$SUPRA_ROOT")
PROJECT_NAMES=("CRIBA" "SUPRA")
if [ -n "$THEKEY_ROOT" ] && [ -d "$THEKEY_ROOT" ]; then
    PROJECT_ROOTS+=("$THEKEY_ROOT")
    PROJECT_NAMES+=("THEKEY")
fi

# --- Tool availability (project environments via uv run) ---
echo ""
echo "--- Tool availability (project environments via uv run) ---"
for i in "${!PROJECT_ROOTS[@]}"; do
    proj="${PROJECT_ROOTS[$i]}"
    echo "  Project: ${PROJECT_NAMES[$i]} ($proj)"
    for tool in ruff bandit semgrep pip-audit pre-commit; do
        if (cd "$proj" && uv run "$tool" --version >/dev/null 2>&1); then
            ver=$(cd "$proj" && uv run "$tool" --version 2>&1 | { IFS= read -r line; printf '%s\n' "$line"; })
            echo "    [OK] $tool : $ver"
        else
            echo "    [MISSING] $tool"
        fi
    done
done

# --- Project directories ---
echo ""
echo "--- Project directories ---"
for i in "${!PROJECT_ROOTS[@]}"; do
    proj="${PROJECT_ROOTS[$i]}"
    if [ -d "$proj" ]; then
        echo "  [OK] ${PROJECT_NAMES[$i]}: $proj"
        if [ -f "$proj/.git/HEAD" ]; then
            echo "    git ref: $(<"$proj/.git/HEAD")"
        fi
    else
        echo "  [MISSING] ${PROJECT_NAMES[$i]}: $proj"
    fi
done

# --- Pre-commit configs ---
echo ""
echo "--- Pre-commit configs ---"
for i in "${!PROJECT_ROOTS[@]}"; do
    proj="${PROJECT_ROOTS[$i]}"
    if [ -f "$proj/.pre-commit-config.yaml" ]; then
        echo "  [OK] ${PROJECT_NAMES[$i]}: .pre-commit-config.yaml"
    else
        echo "  [MISSING] ${PROJECT_NAMES[$i]}: .pre-commit-config.yaml"
    fi
done

# --- Secret scan ---
echo ""
echo "--- Secret scan (gitleaks on CRIBA) ---"
if command -v gitleaks >/dev/null 2>&1; then
    if (cd "$CRIBA_ROOT" && gitleaks detect --source . --verbose); then
        echo "  CRIBA: gitleaks completed"
    else
        echo "  CRIBA: gitleaks reported findings or failed"
    fi
else
    echo "  CRIBA: gitleaks unavailable"
fi

echo ""
echo "=== Verification complete ==="