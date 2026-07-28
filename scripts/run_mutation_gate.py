"""Run one bounded mutmut shard and enforce a quantitative score."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_STATUS_PATTERNS = {
    "killed": re.compile(r"🎉\s*(\d+)"),
    "no_tests": re.compile(r"🫥\s*(\d+)"),
    "timeout": re.compile(r"⏰\s*(\d+)"),
    "suspicious": re.compile(r"🤔\s*(\d+)"),
    "survived": re.compile(r"🙁\s*(\d+)"),
    "skipped": re.compile(r"🔇\s*(\d+)"),
}


def parse_mutmut_summary(output: str) -> dict[str, int]:
    """Parse the last mutmut 3 progress summary, independent of ANSI color."""
    clean = _ANSI.sub("", output.replace("\r", "\n"))
    parsed = {name: 0 for name in _STATUS_PATTERNS}
    for line in clean.splitlines():
        current: dict[str, int] = {}
        for name, pattern in _STATUS_PATTERNS.items():
            match = pattern.search(line)
            if match:
                current[name] = int(match.group(1))
        if current:
            parsed.update(current)
    return parsed


def run_shard(target: str, minimum_score: float) -> tuple[int, dict[str, Any]]:
    """Execute a clean mutation shard and return an evidence report."""
    command = [sys.executable, "-m", "mutmut", "run", target, "--max-children", "2"]
    completed = subprocess.run(
        command,
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        timeout=6_900,
        check=False,
    )
    combined = completed.stdout + "\n" + completed.stderr
    counts = parse_mutmut_summary(combined)
    scored = counts["killed"] + counts["survived"]
    score = 100.0 * counts["killed"] / scored if scored else 0.0
    infrastructure_failures = (
        completed.returncode not in {0, 1}
        or scored == 0
        or counts["timeout"] > 0
        or counts["suspicious"] > 0
        or counts["no_tests"] > 0
    )
    passed = not infrastructure_failures and score >= minimum_score
    report: dict[str, Any] = {
        "schema_version": "1.0.0",
        "target": target,
        "command": command,
        "mutmut_return_code": completed.returncode,
        "counts": counts,
        "mutation_score": round(score, 4),
        "minimum_score": minimum_score,
        "infrastructure_failures": infrastructure_failures,
        "passed": passed,
        "raw_output": combined,
    }
    return (0 if passed else 1), report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--minimum-score", type=float, default=80.0)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        return_code, report = run_shard(args.target, args.minimum_score)
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        report = {
            "schema_version": "1.0.0",
            "target": args.target,
            "passed": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
        return_code = 2
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
