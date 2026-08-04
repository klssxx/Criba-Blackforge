from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import modal

REMOTE_ROOT = Path("/workspace")
ARTIFACT_ROOT = Path("/artifacts")

if modal.is_local():
    HOST_ROOT = Path(__file__).resolve().parents[2]
else:
    # No evaluar parents[2] dentro del worker remoto.
    HOST_ROOT = REMOTE_ROOT

MANIFEST_LOCAL = (
    HOST_ROOT
    / ".autoregen"
    / "cloud"
    / "verification_manifest.json"
)

IGNORE = [
    ".git/**",
    ".venv/**",
    "**/__pycache__/**",
    ".pytest_cache/**",
    ".mypy_cache/**",
    ".ruff_cache/**",
    "dist/**",
    "build/**",
    "artifacts/**",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    ".env",
    ".env.*",
    "**/*token*",
    "**/*secret*",
]

base_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git")
)

if (HOST_ROOT / "uv.lock").exists():
    image = base_image.uv_sync(str(HOST_ROOT), frozen=True)
elif (HOST_ROOT / "pyproject.toml").exists():
    image = base_image.pip_install_from_pyproject(str(HOST_ROOT / "pyproject.toml"))
elif (HOST_ROOT / "requirements.txt").exists():
    image = base_image.pip_install_from_requirements(str(HOST_ROOT / "requirements.txt"))
else:
    image = base_image

image = (
    image.uv_pip_install(
        "pytest>=8",
        "pytest-cov>=5",
        "pytest-timeout>=2.4",
        "mypy>=1.10",
        "ruff>=0.6",
        "hypothesis>=6",
        "jsonschema>=4.22",
        "pydantic>=2",
        "mutmut>=3.5",
        "httpx>=0.27",
    )
    .env(
        {
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": "/workspace/src:/workspace",
        }
    )
    .workdir("/workspace")
    .add_local_dir(str(HOST_ROOT), remote_path="/workspace", ignore=IGNORE)
)

app = modal.App("criba-verification-fabric")
volume = modal.Volume.from_name("criba-verification-artifacts", create_if_missing=True)
ARTIFACT_ROOT_STR = "/artifacts"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_hash(root: Path = REMOTE_ROOT) -> str:
    digest = hashlib.sha256()
    include_roots = [root / "src", root / "tests", root / "pyproject.toml"]
    files: list[Path] = []
    for entry in include_roots:
        if entry.is_file():
            files.append(entry)
        elif entry.is_dir():
            files.extend(p for p in entry.rglob("*") if p.is_file())
    for path in sorted(files, key=lambda p: p.as_posix()):
        rel = path.relative_to(root).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _load_manifest() -> dict[str, Any]:
    path = REMOTE_ROOT / ".autoregen" / "cloud" / "verification_manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _new_run_dir(source_hash: str, gate_id: str) -> Path:
    safe_gate = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in gate_id)
    run_id = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        + "-" + source_hash[:12] + "-" + safe_gate
    )
    path = ARTIFACT_ROOT / run_id
    path.mkdir(parents=True, exist_ok=True)
    current = ARTIFACT_ROOT / "current"
    current.mkdir(parents=True, exist_ok=True)
    return path


def _run_command(gate_id: str, command: list[str], run_dir: Path, timeout: int = 7200) -> dict[str, Any]:
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=REMOTE_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
        check=False,
        env={**os.environ, "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED", "0")},
    )
    duration = time.monotonic() - started
    stdout_path = run_dir / f"{gate_id}.stdout.txt"
    stderr_path = run_dir / f"{gate_id}.stderr.txt"
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    return {
        "gate": gate_id,
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "command": command,
        "exit_code": completed.returncode,
        "duration_seconds": round(duration, 3),
        "stdout_artifact": str(stdout_path),
        "stderr_artifact": str(stderr_path),
    }


def _scope_guard(manifest: dict[str, Any]) -> dict[str, Any]:
    forbidden = manifest["scope"]["forbidden_phase_paths"]
    present = [path for path in forbidden if (REMOTE_ROOT / path).exists()]
    return {
        "gate": "scope_guard",
        "status": "PASS" if not present else "FAIL",
        "forbidden_paths_present": present,
    }


def _feature_flags() -> dict[str, Any]:
    constants = REMOTE_ROOT / "src" / "criba" / "constants.py"
    if not constants.exists():
        return {"gate": "feature_flags", "status": "BLOCKED", "reason": "constants.py missing"}
    text = constants.read_text(encoding="utf-8")
    checks = {
        "compound_personas_off": (
            '"compound_personas": False' in text
            or "'compound_personas': False" in text
            or "compound_personas=False" in text
        ),
        "ensemble_analysis_off": (
            '"ensemble_analysis": False' in text
            or "'ensemble_analysis': False" in text
            or "ensemble_analysis=False" in text
        ),
    }
    return {
        "gate": "feature_flags",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
    }


def _validate_hy3_review(review_text: str, source_hash: str) -> dict[str, Any]:
    from jsonschema import Draft202012Validator

    schema_path = REMOTE_ROOT / "schemas" / "hy3_review.schema.json"
    if not schema_path.exists():
        return {"gate": "hy3_review", "status": "BLOCKED", "reason": "review schema missing"}
    try:
        payload = json.loads(review_text)
    except json.JSONDecodeError as exc:
        return {"gate": "hy3_review", "status": "FAIL", "reason": f"invalid JSON: {exc}"}
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda e: list(e.path))
    if errors:
        return {
            "gate": "hy3_review",
            "status": "FAIL",
            "errors": [error.message for error in errors],
        }
    source_matches = payload.get("source_hash") == source_hash
    severe = [
        finding
        for finding in payload.get("findings", [])
        if finding.get("severity") in {"BLOCKER", "HIGH"}
    ]
    valid_semantics = (
        payload.get("persona_separation", {}).get("is_structurally_distinct") is True
        and payload.get("minority_preservation", {}).get("is_unambiguous") is True
        and payload.get("scope_compliance", {}).get("p3_to_p10_untouched") is True
    )
    status = "PASS" if source_matches and not severe and valid_semantics else "FAIL"
    return {
        "gate": "hy3_review",
        "status": status,
        "source_hash_matches": source_matches,
        "blocker_or_high_findings": severe,
        "semantic_invariants": valid_semantics,
        "review_verdict": payload.get("verdict"),
    }


@app.function(image=image, volumes={ARTIFACT_ROOT_STR: volume}, timeout=24 * 60 * 60, cpu=4, memory=8192)
def execute_gate(gate: dict[str, Any], source_hash: str, review_text: str = "") -> dict[str, Any]:
    manifest = _load_manifest()
    gate_id = str(gate["gate_id"])
    run_dir = _new_run_dir(source_hash, gate_id)

    missing = gate.get("blocked_if_missing")
    if missing and not (REMOTE_ROOT / str(missing)).exists():
        result = {
            "gate": gate_id,
            "status": "BLOCKED",
            "reason": f"optional test path missing: {missing}",
            "required": bool(gate.get("required", False)),
        }
    elif gate.get("builtin") == "scope_guard":
        result = _scope_guard(manifest)
    elif gate.get("builtin") == "feature_flags":
        result = _feature_flags()
    elif gate.get("builtin") == "hy3_review":
        if not review_text:
            result = {"gate": gate_id, "status": "BLOCKED", "reason": "Hy3 review not supplied"}
        else:
            result = _validate_hy3_review(review_text, source_hash)
    elif gate.get("builtin") == "determinism":
        repetitions = int(gate.get("repetitions", 3))
        command = ["python", "-m", "pytest", "tests/unit/test_personas.py", "-q"]
        runs = []
        for index in range(repetitions):
            env_seed = str(index)
            started = time.monotonic()
            completed = subprocess.run(
                command,
                cwd=REMOTE_ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=7200,
                check=False,
                env={**os.environ, "PYTHONHASHSEED": env_seed},
            )
            runs.append({
                "seed": env_seed,
                "exit_code": completed.returncode,
                "stdout_hash": _sha256_bytes(completed.stdout.encode("utf-8")),
                "duration_seconds": round(time.monotonic() - started, 3),
            })
        result = {
            "gate": gate_id,
            "status": "PASS" if all(run["exit_code"] == 0 for run in runs) else "FAIL",
            "runs": runs,
        }
    else:
        result = _run_command(gate_id, list(gate["command"]), run_dir)
        pass_codes = set(gate.get("pass_exit_codes", [0]))
        result["status"] = "PASS" if result["exit_code"] in pass_codes else "FAIL"

    result.update(
        {
            "required": bool(gate.get("required", False)),
            "severity": gate.get("severity", "medium"),
            "source_hash": source_hash,
            "environment": {
                "python": platform.python_version(),
                "platform": platform.platform(),
            },
            "timestamp_utc": _utc_now(),
        }
    )
    (run_dir / f"{gate_id}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    volume.commit()
    return result


@app.function(image=image)
def probe_paths() -> dict[str, object]:
    return {
        "modal_is_local": modal.is_local(),
        "file": __file__,
        "cwd": str(Path.cwd()),
        "workspace_exists": Path("/workspace").is_dir(),
        "manifest_exists": Path(
            "/workspace/.autoregen/cloud/verification_manifest.json"
        ).is_file(),
        "personas_exists": Path(
            "/workspace/src/criba/personas.py"
        ).is_file(),
        "tests_exist": Path("/workspace/tests").is_dir(),
    }


@app.local_entrypoint()
def probe() -> None:
    print(json.dumps(probe_paths.remote(), ensure_ascii=False, indent=2))


@app.local_entrypoint()
def main(action: str = "all", hy3_review_path: str = "") -> None:
    manifest = json.loads(MANIFEST_LOCAL.read_text(encoding="utf-8"))
    source_hash = _source_hash(HOST_ROOT)

    review_text = ""
    if hy3_review_path:
        review_path = Path(hy3_review_path)
        if not review_path.is_absolute():
            review_path = HOST_ROOT / review_path
        if review_path.exists():
            review_text = review_path.read_text(encoding="utf-8")

    gates = manifest["gates"]
    if action == "environment":
        gates = [gate for gate in gates if gate["gate_id"] == "environment"]
    elif action == "p2":
        wanted = {
            "p2_tests", "mypy_p2", "ruff_p2", "scope_guard",
            "feature_flags", "determinism", "hy3_review"
        }
        gates = [gate for gate in gates if gate["gate_id"] in wanted]
    elif action != "all":
        gates = [gate for gate in gates if gate["gate_id"] == action]
        if not gates:
            raise SystemExit(f"Unknown action: {action}")

    results = list(
        execute_gate.map(
            gates,
            kwargs={"source_hash": source_hash, "review_text": review_text},
            order_outputs=False,
        )
    )

    required_failures = [
        result for result in results
        if result.get("required") and result.get("status") == "FAIL"
    ]
    high_failures = [
        result for result in results
        if result.get("severity") in {"critical", "high"} and result.get("status") == "FAIL"
    ]
    infra = [result for result in results if result.get("status") == "INFRA_ERROR"]
    blocked = [result for result in results if result.get("status") == "BLOCKED"]

    if infra:
        verdict = "INFRA_ERROR"
    elif required_failures or high_failures:
        verdict = "FAILED"
    elif blocked:
        verdict = "PARTIAL"
    else:
        verdict = "VERIFIED"

    summary = {
        "manifest_version": manifest["manifest_version"],
        "project": manifest["project"],
        "phase": manifest["active_phase"],
        "source_hash": source_hash,
        "verdict": verdict,
        "results": sorted(results, key=lambda item: item["gate"]),
        "generated_at_utc": _utc_now(),
    }
    output_path = HOST_ROOT / "artifacts" / "modal" / "latest-result.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
