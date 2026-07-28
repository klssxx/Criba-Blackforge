"""Verify P2 output determinism across fresh processes and hash seeds."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


_CHILD = r"""
import json
from criba.personas import run_personas

packet = {
    "original_query": "Reducir fraude en pagos sin elevar la fricción.",
    "intent": "INNOVAR",
    "model_instruction": "Conservar incertidumbre y no inventar evidencia.",
    "innovation": {
        "known_space": ["reglas estáticas", "revisión manual"],
        "assumptions": ["más control implica más fricción"],
        "ruptures": [{"operation": "invertir", "result": "evaluar señales antes del pago"}],
    },
    "protected_assets": ["cuentas de pago"],
    "authorization_state": "pending",
}
print(json.dumps(
    [result.model_dump(mode="json") for result in run_personas(packet)],
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
))
"""


def run_probe(repetitions: int) -> dict[str, Any]:
    """Run isolated probes and return their content-addressed comparison."""
    if repetitions < 2:
        raise ValueError("repetitions must be at least 2")
    hashes: list[str] = []
    outputs: list[str] = []
    for index in range(repetitions):
        env = dict(os.environ)
        env["PYTHONHASHSEED"] = str(1000 + index)
        env["PYTHONPATH"] = str(Path.cwd() / "src")
        completed = subprocess.run(
            [sys.executable, "-c", _CHILD],
            cwd=Path.cwd(),
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"determinism child {index} failed rc={completed.returncode}: {completed.stderr}"
            )
        output = completed.stdout.strip()
        outputs.append(output)
        hashes.append(hashlib.sha256(output.encode("utf-8")).hexdigest())
    return {
        "schema_version": "1.0.0",
        "repetitions": repetitions,
        "unique_outputs": len(set(outputs)),
        "sha256": hashes,
        "deterministic": len(set(outputs)) == 1,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        report = run_probe(args.repetitions)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"determinism probe error: {exc}", file=sys.stderr)
        return 2
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["deterministic"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
