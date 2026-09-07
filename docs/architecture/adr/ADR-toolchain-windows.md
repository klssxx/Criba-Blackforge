# Skill: windows-toolchain-audit

> HISTORICAL REFERENCE (2026-09-03): path examples in this ADR are not current
> execution roots. Use `docs/TOOLCHAIN.md` and resolve roots from the scripts.

**Trigger**: User asks to audit/install/verify a full security + dev toolchain on Windows (gitleaks, trivy, osv-scanner, syft, grype, semgrep, bandit, pip-audit, pre-commit, etc.) across multiple Python/uv projects.

## Body

### Strategy: split system PATH vs project venv

| Tool class | Where installed | Why |
|------------|----------------|-----|
| Static analysis scanners (gitleaks, trivy, osv-scanner, syft, grype) | System PATH via **winget** | Windows-native binaries; shared across all projects |
| Python-specific (semgrep, bandit, pip-audit, pre-commit, ruff) | Declared in `pyproject.toml`, resolved by `uv sync` | Reproducible per project via `uv.lock` |

### Common pitfall: terminal output truncation

On this Windows host, `terminal` tool output is frequently truncated to ~1 line. When verifying tool versions, run each tool individually or use a **verification script** that writes results to a file and reads back:

```bash
# Example: check all tools, write to file
{
  for t in git gh python uv node pnpm docker rg fd jq; do
    echo "$t: $(which $t 2>/dev/null || echo MISSING) -> ($($t --version 2>&1 | head -1))"
  done
} > /c/Users/KLSX/verify_toolchain.txt
```

### Idempotency rule

Re-running the procedure must not reinstall working tools. The verification script checks `command -v` before attempting any action.

### Windows path quirk

When running scripts from `/e/PROJECTS/...` in git-bash/MSYS, `cd` works but native tools receive POSIX paths. Always use `workdir=` explicitly in the terminal tool to avoid cwd corruption cascades.

### Verification script template

See `scripts/verify-dev-environment.sh` — a single script that checks:
1. System PATH tools (git, gh, uv, node, docker, ripgrep, fd, jq, gitleaks, trivy, osv-scanner, syft, grype)
2. Per-project `uv sync` dev environment (ruff, bandit, semgrep, pip-audit, pre-commit)
3. Project directories and git branches
4. Pre-commit config presence
5. Secret scan (gitleaks detect)

### Tool versions (as of 2026-09-03)

| Tool | Method | Version |
|------|--------|---------|
| gitleaks | winget | 8.30.1 |
| trivy | winget | 0.74.0 |
| osv-scanner | winget | 2.4.0 |
| syft | winget | 1.51.0 |
| grype | winget | 0.118.0 |
| semgrep | uv sync | 1.176.0 |
| bandit | uv sync | 1.9.4 |
| pip-audit | uv sync | 2.10.1 |
| pre-commit | uv sync | 4.6.2 |
| ruff | uv sync | 0.16.5 (CRIBA/SUPRA), 0.15.21 (THEKEY) |
