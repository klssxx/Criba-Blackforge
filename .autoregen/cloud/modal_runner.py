"""Modal Verification Fabric for CRIBA + BLACKFORGE.

The ``fabric`` entrypoint fans independent gates out with ``Function.map()``,
collects structured results, calculates an automatic verdict, writes a
self-hashed local manifest, and persists the same evidence in a Modal Volume.

Legacy focused entrypoints remain available for fast iteration:

    python -m modal run .autoregen/cloud/modal_runner.py::pytest_full
    python -m modal run .autoregen/cloud/modal_runner.py::pytest_file --path tests/unit/test_personas.py
    python -m modal run .autoregen/cloud/modal_runner.py::mypy_strict --target src/criba/personas.py

P2 fabric:

    python -m modal run .autoregen/cloud/modal_runner.py::fabric --profile p2
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping
import xml.etree.ElementTree as ET

import modal


_here = pathlib.Path(__file__).resolve()
REPO_ROOT = _here.parents[2] if len(_here.parents) >= 3 else _here.parent
REMOTE_ROOT = "/work"
ARTIFACT_MOUNT = pathlib.Path("/fabric-artifacts")
ARTIFACT_VOLUME_NAME = "criba-verification-artifacts"

# These are the exact source inputs mounted into the reproducible image and
# hashed into every manifest.  Local environments, Git data, and caches are
# deliberately excluded.
_INCLUDE = [
    ".autoregen/cloud/modal_runner.py",
    "src",
    "tests",
    "benchmarks",
    "scripts",
    "imports",
    "data",
    "verification",
    "pyproject.toml",
    "uv.lock",
    "CRIBA-Blackforge.spec",
]

_PINNED_PACKAGES = (
    "pytest==9.1.1",
    "pytest-cov==7.1.0",
    "pytest-timeout==2.4.0",
    "coverage==7.15.1",
    "mypy==2.3.0",
    "pydantic==2.13.4",
    "fastapi==0.140.0",
    "httpx==0.28.1",
    "hypothesis==6.161.1",
    "ruff==0.12.12",
    "mutmut==3.6.0",
)

image = modal.Image.debian_slim(python_version="3.12").pip_install(*_PINNED_PACKAGES)
for _item in _INCLUDE:
    _local = REPO_ROOT / _item
    if _local.exists():
        _remote = f"{REMOTE_ROOT}/{_item}"
        image = (
            image.add_local_dir(str(_local), _remote)
            if _local.is_dir()
            else image.add_local_file(str(_local), _remote)
        )

artifact_volume = modal.Volume.from_name(ARTIFACT_VOLUME_NAME, create_if_missing=True)
app = modal.App("criba-verification-fabric", image=image)

_FOCUSED_FUNCTION = dict(cpu=2.0, memory=4096, timeout=900)
_FABRIC_WORKER = dict(
    cpu=2.0,
    memory=4096,
    timeout=7_200,
    retries=modal.Retries(
        max_retries=2,
        backoff_coefficient=2.0,
        initial_delay=1.0,
        max_delay=8.0,
    ),
)


def _fabric_imports() -> tuple[Any, ...]:
    """Import pure fabric contracts in local and cloud execution contexts."""
    scripts_path = pathlib.Path(REMOTE_ROOT) / "scripts"
    local_scripts = REPO_ROOT / "scripts"
    for candidate in (scripts_path, local_scripts):
        if candidate.exists() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))
    from verification_fabric import (
        GateResult,
        GateSpec,
        build_manifest,
        build_source_snapshot,
        profile_gate_specs,
        verify_manifest,
    )

    return (
        GateResult,
        GateSpec,
        build_manifest,
        build_source_snapshot,
        profile_gate_specs,
        verify_manifest,
    )


def _base_env() -> dict[str, str]:
    """Return deterministic process settings without dropping required OS vars."""
    env = dict(os.environ)
    env.update(
        {
            "PYTHONPATH": f"{REMOTE_ROOT}/src:{REMOTE_ROOT}",
            "MYPYPATH": f"{REMOTE_ROOT}/src",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "TZ": "UTC",
            "LC_ALL": "C.UTF-8",
            "LANG": "C.UTF-8",
            "COLUMNS": "160",
            "TERM": "dumb",
        }
    )
    return env


def _run(cmd: list[str]) -> int:
    """Run a focused command in the container and stream its exact result."""
    print(f"[cloud] $ {' '.join(cmd)}", flush=True)
    proc = subprocess.run(
        cmd,
        cwd=REMOTE_ROOT,
        env=_base_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    print(f"[cloud] exit_code={proc.returncode}", flush=True)
    return proc.returncode


@app.function(**_FOCUSED_FUNCTION)
def _pytest_full() -> int:
    return _run(
        [
            "python",
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            "-q",
            "--timeout=60",
            "--timeout-method=thread",
            f"{REMOTE_ROOT}/tests",
        ]
    )


@app.function(**_FOCUSED_FUNCTION)
def _pytest_file(path: str) -> int:
    return _run(
        [
            "python",
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            "-v",
            "--timeout=30",
            "--timeout-method=thread",
            "-rA",
            f"{REMOTE_ROOT}/{path}",
        ]
    )


@app.function(**_FOCUSED_FUNCTION)
def _mypy_strict(target: str) -> int:
    return _run(["python", "-m", "mypy", "--strict", f"{REMOTE_ROOT}/{target}"])


@app.function(**_FOCUSED_FUNCTION)
def _mypy_config() -> int:
    return _run(["python", "-m", "mypy", "src/criba"])


@app.function(**_FOCUSED_FUNCTION)
def _coverage_run() -> int:
    return _run(
        [
            "python",
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            "--cov=src/criba",
            "--cov-branch",
            "--cov-report=term-missing",
            "-q",
            f"{REMOTE_ROOT}/tests",
        ]
    )


@app.function(**_FOCUSED_FUNCTION)
def _benchmark_blackforge(repetitions: int) -> dict[str, object]:
    sys.path.insert(0, REMOTE_ROOT)
    sys.path.insert(0, f"{REMOTE_ROOT}/src")
    from benchmarks.blackforge_benchmark import run_benchmark

    return run_benchmark(repetitions)


@app.function(**_FABRIC_WORKER)
def _run_fabric_gate(raw_spec: Mapping[str, Any]) -> dict[str, Any]:
    """Execute one independent map input and return structured evidence."""
    GateResult, GateSpec, *_ = _fabric_imports()
    try:
        spec = GateSpec.from_dict(raw_spec)
    except (TypeError, ValueError) as exc:
        return GateResult(
            gate_id=str(raw_spec.get("gate_id", "invalid_gate")),
            category=str(raw_spec.get("category", "infrastructure")),
            required=True,
            status="error",
            return_code=2,
            duration_seconds=0.0,
            command=(),
            stdout="",
            stderr="",
            error=f"invalid GateSpec: {exc}",
        ).to_dict()

    artifact_dir = pathlib.Path(tempfile.mkdtemp(prefix=f"fabric-{spec.gate_id}-"))
    command = tuple(
        item.replace("{artifact_dir}", str(artifact_dir))
        for item in spec.command
    )
    started = time.monotonic()
    try:
        completed = subprocess.run(
            list(command),
            cwd=REMOTE_ROOT,
            env=_base_env(),
            capture_output=True,
            text=True,
            timeout=spec.command_timeout_seconds,
            check=False,
        )
        duration = time.monotonic() - started
        metrics = _extract_metrics(spec, artifact_dir)
        artifacts = _collect_artifacts(spec, artifact_dir)
        status = "passed" if completed.returncode == 0 else "failed"
        return GateResult(
            gate_id=spec.gate_id,
            category=spec.category,
            required=spec.required,
            status=status,
            return_code=completed.returncode,
            duration_seconds=round(duration, 6),
            command=command,
            stdout=completed.stdout,
            stderr=completed.stderr,
            metrics=metrics,
            artifacts=artifacts,
        ).to_dict()
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - started
        return GateResult(
            gate_id=spec.gate_id,
            category=spec.category,
            required=spec.required,
            status="error",
            return_code=124,
            duration_seconds=round(duration, 6),
            command=command,
            stdout=_decoded_timeout_stream(exc.stdout),
            stderr=_decoded_timeout_stream(exc.stderr),
            error=f"command timeout after {spec.command_timeout_seconds}s",
        ).to_dict()
    except OSError as exc:
        duration = time.monotonic() - started
        return GateResult(
            gate_id=spec.gate_id,
            category=spec.category,
            required=spec.required,
            status="error",
            return_code=127,
            duration_seconds=round(duration, 6),
            command=command,
            stdout="",
            stderr="",
            error=f"{type(exc).__name__}: {exc}",
        ).to_dict()
    finally:
        shutil.rmtree(artifact_dir, ignore_errors=True)


@app.function(
    cpu=1.0,
    memory=1024,
    timeout=600,
    retries=modal.Retries(max_retries=2, initial_delay=1.0, max_delay=8.0),
    volumes={str(ARTIFACT_MOUNT): artifact_volume},
)
def _persist_fabric_bundle(bundle: Mapping[str, Any]) -> str:
    """Persist one immutable run bundle with a single Volume writer."""
    run_id = str(bundle["run_id"])
    target = ARTIFACT_MOUNT / run_id
    target.mkdir(parents=True, exist_ok=False)
    manifest = bundle["manifest"]
    (target / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = {
        "run_id": run_id,
        "profile": manifest["profile"],
        "verdict": manifest["verdict"],
        "verdict_reasons": manifest["verdict_reasons"],
        "manifest_sha256": manifest["manifest_sha256"],
    }
    (target / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for log in bundle.get("logs", []):
        gate_id = str(log["gate_id"])
        logs_dir = target / "logs"
        logs_dir.mkdir(exist_ok=True)
        (logs_dir / f"{gate_id}.stdout.txt").write_text(
            str(log.get("stdout", "")), encoding="utf-8"
        )
        (logs_dir / f"{gate_id}.stderr.txt").write_text(
            str(log.get("stderr", "")), encoding="utf-8"
        )
    for artifact in bundle.get("artifacts", []):
        relative = pathlib.PurePosixPath(str(artifact["path"]))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe artifact path: {relative}")
        destination = target / "gate-artifacts" / pathlib.Path(*relative.parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(str(artifact["content"]), encoding="utf-8")
    artifact_volume.commit()
    return f"{ARTIFACT_VOLUME_NAME}:/{run_id}"


def _extract_metrics(spec: Any, artifact_dir: pathlib.Path) -> dict[str, float]:
    metrics: dict[str, float] = {}
    if spec.minimum_coverage_percent is not None:
        path = artifact_dir / "p2-coverage.xml"
        if path.exists():
            root = ET.parse(path).getroot()
            metrics["coverage_percent"] = round(float(root.attrib["line-rate"]) * 100.0, 4)
    if spec.minimum_mutation_score is not None:
        for name in spec.artifact_paths:
            path = artifact_dir / name
            if not path.exists():
                continue
            value = json.loads(path.read_text(encoding="utf-8"))
            if "mutation_score" in value:
                metrics["mutation_score"] = float(value["mutation_score"])
                break
    return metrics


def _collect_artifacts(spec: Any, artifact_dir: pathlib.Path) -> tuple[dict[str, Any], ...]:
    _fabric_imports()
    from verification_fabric import sha256_bytes

    artifacts: list[dict[str, Any]] = []
    for name in spec.artifact_paths:
        path = artifact_dir / name
        if not path.exists() or not path.is_file():
            continue
        content = path.read_bytes()
        artifacts.append(
            {
                "path": f"{spec.gate_id}/{name}",
                "size": len(content),
                "sha256": sha256_bytes(content),
                "content": content.decode("utf-8", errors="replace"),
            }
        )
    return tuple(artifacts)


def _decoded_timeout_stream(value: str | bytes | None) -> str:
    if value is None:
        return ""
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value


def _report_result(rc: int, label: str) -> None:
    print(f"\n=== RESULT rc={rc} ({label}) ===")
    if rc != 0:
        raise SystemExit(rc)


@app.local_entrypoint()
def pytest_full() -> None:
    _report_result(_pytest_full.remote(), "pytest full")


@app.local_entrypoint()
def pytest_file(path: str) -> None:
    _report_result(_pytest_file.remote(path), path)


@app.local_entrypoint()
def mypy_strict(target: str = "src/criba") -> None:
    _report_result(_mypy_strict.remote(target), f"mypy {target}")


@app.local_entrypoint()
def mypy_scoped(exclude: str = "gui.py") -> None:
    del exclude
    _report_result(_mypy_config.remote(), "mypy src/criba via pyproject config")


@app.local_entrypoint()
def coverage_run() -> None:
    _report_result(_coverage_run.remote(), "coverage")


@app.local_entrypoint()
def benchmark_blackforge(
    repetitions: int = 3,
    output: str = "verification/blackforge_benchmark.json",
) -> None:
    report = _benchmark_blackforge.remote(repetitions)
    output_path = pathlib.Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n=== RESULT rc=0 (benchmark -> {output_path}) ===")


@app.local_entrypoint()
def fabric_gate(gate_id: str, profile: str = "p2") -> None:
    """Run one named fabric gate remotely for focused diagnosis."""
    GateResult, _, _, _, profile_gate_specs, _ = _fabric_imports()
    specs = [spec for spec in profile_gate_specs(profile) if spec.gate_id == gate_id]
    if len(specs) != 1:
        available = ", ".join(spec.gate_id for spec in profile_gate_specs(profile))
        raise ValueError(f"unknown gate_id {gate_id!r}; available: {available}")

    result = GateResult.from_dict(_run_fabric_gate.remote(specs[0].to_dict()))
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    print(
        f"[fabric] {result.gate_id}: {result.status} rc={result.return_code} "
        f"duration={result.duration_seconds:.3f}s metrics={dict(result.metrics)}"
    )
    if result.status != "passed":
        raise SystemExit(result.return_code or 1)


@app.local_entrypoint()
def fabric(
    profile: str = "p2",
    output: str = "artifacts/verification-fabric",
) -> None:
    """Run a parallel profile and persist its automatically gated evidence."""
    (
        GateResult,
        _,
        build_manifest,
        build_source_snapshot,
        profile_gate_specs,
        verify_manifest,
    ) = _fabric_imports()
    specs = profile_gate_specs(profile)
    source_snapshot = build_source_snapshot(REPO_ROOT, _INCLUDE)
    timestamp = datetime.now(timezone.utc)
    run_id = (
        f"{timestamp.strftime('%Y%m%dT%H%M%SZ')}-"
        f"{profile}-{source_snapshot['sha256'][:12]}"
    )
    print(f"[fabric] run_id={run_id} profile={profile} gates={len(specs)}")
    print("[fabric] dispatch=Function.map order_outputs=True return_exceptions=True")

    raw_outputs = list(
        _run_fabric_gate.map(
            [spec.to_dict() for spec in specs],
            order_outputs=True,
            return_exceptions=True,
        )
    )
    results = []
    for spec, raw in zip(specs, raw_outputs):
        if isinstance(raw, BaseException):
            results.append(
                GateResult(
                    gate_id=spec.gate_id,
                    category=spec.category,
                    required=spec.required,
                    status="error",
                    return_code=2,
                    duration_seconds=0.0,
                    command=spec.command,
                    stdout="",
                    stderr="",
                    error=f"Modal map input failed: {type(raw).__name__}: {raw}",
                )
            )
        else:
            results.append(GateResult.from_dict(raw))

    artifacts: list[dict[str, Any]] = []
    clean_results = []
    for result in results:
        clean_artifacts = []
        for artifact in result.artifacts:
            materialized = dict(artifact)
            content = str(materialized.pop("content", ""))
            artifacts.append(dict(materialized, content=content))
            clean_artifacts.append(materialized)
        clean_results.append(replace(result, artifacts=tuple(clean_artifacts)))

    execution = {
        "provider": "modal",
        "app": "criba-verification-fabric",
        "parallel_dispatch": "Function.map",
        "map_inputs": len(specs),
        "order_outputs": True,
        "return_exceptions": True,
        "function_timeout_seconds": 7_200,
        "command_timeout_max_seconds": max(spec.command_timeout_seconds for spec in specs),
        "retries": {
            "max_retries": 2,
            "backoff_coefficient": 2.0,
            "initial_delay_seconds": 1.0,
            "scope": "infrastructure/container failure per map input",
        },
        "artifact_volume": ARTIFACT_VOLUME_NAME,
    }
    manifest = build_manifest(
        run_id=run_id,
        profile=profile,
        source_snapshot=source_snapshot,
        specs=specs,
        results=clean_results,
        created_at_utc=timestamp.isoformat().replace("+00:00", "Z"),
        execution=execution,
    )
    verified, verification_message = verify_manifest(manifest)
    if not verified:
        raise RuntimeError(f"generated manifest failed self-verification: {verification_message}")

    local_dir = pathlib.Path(output) / run_id
    local_dir.mkdir(parents=True, exist_ok=False)
    local_manifest = local_dir / "manifest.json"
    local_manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for result in clean_results:
        print(
            f"[fabric] {result.gate_id}: {result.status} rc={result.return_code} "
            f"duration={result.duration_seconds:.3f}s metrics={dict(result.metrics)}"
        )
    remote_path = _persist_fabric_bundle.remote(
        {
            "run_id": run_id,
            "manifest": manifest,
            "artifacts": artifacts,
            "logs": [
                {
                    "gate_id": result.gate_id,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
                for result in clean_results
            ],
        }
    )
    print(f"[fabric] manifest={local_manifest}")
    print(f"[fabric] persistent_evidence={remote_path}")
    print(f"[fabric] manifest_sha256={manifest['manifest_sha256']}")
    print(f"[fabric] verdict={manifest['verdict']}")
    if manifest["verdict_reasons"]:
        for reason in manifest["verdict_reasons"]:
            print(f"[fabric] reason={reason}")
    if manifest["verdict"] != "PASS":
        raise SystemExit(1)


@app.local_entrypoint()
def verify_fabric_manifest(path: str) -> None:
    """Verify a previously downloaded/local manifest without trusting its verdict."""
    *_, verify_manifest = _fabric_imports()
    manifest = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    verified, message = verify_manifest(manifest)
    print(message)
    if not verified:
        raise SystemExit(1)
