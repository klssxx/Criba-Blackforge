"""Modal cloud runner for CRIBA + BLACKFORGE hardening verification.

Runs pytest / mypy / coverage in Modal's cloud so the local 16 GB machine is
never loaded. The local repo (source-only, no venv/git/caches) is added to a
container image; the toolchain is installed in the cloud image.

Usage (from E:\\PROYECTS\\CRIBA):
    python -m modal run .autoregen/cloud/modal_runner.py::pytest_full
    python -m modal run .autoregen/cloud/modal_runner.py::pytest_file --path tests/unit/test_blackforge_pipeline.py
    python -m modal run .autoregen/cloud/modal_runner.py::mypy_strict
    python -m modal run .autoregen/cloud/modal_runner.py::coverage_run
    python -m modal run .autoregen/cloud/modal_runner.py::benchmark_blackforge --repetitions 3

All heavy work happens in the cloud container; only text results return locally.
"""
from __future__ import annotations

import json
import pathlib

import modal

# --- Repo layout -----------------------------------------------------------
# This file lives at <repo>/.autoregen/cloud/modal_runner.py locally, but the
# module is ALSO re-imported inside the Modal container (at /root/), where the
# parents[2] path does not exist. Compute the local root defensively so import
# never crashes in the container; the repo files are already baked into the
# image by add_local_dir at build time.
_here = pathlib.Path(__file__).resolve()
REPO_ROOT = _here.parents[2] if len(_here.parents) >= 3 else _here.parent
REMOTE_ROOT = "/work"

# Only the source-of-truth dirs the tests actually need. No .venv/.git/caches.
# verification/ carries the golden master (mvp_output_sample.normalized.json)
# that test_mvp_golden_output.py compares against — required for parity.
_INCLUDE = ["src", "tests", "benchmarks", "imports", "data", "verification", "pyproject.toml"]

# --- Image: toolchain in the cloud, repo copied in -------------------------
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "pytest==9.1.1",
        "pytest-cov==7.1.0",
        "pytest-timeout",
        "coverage==7.15.1",
        "mypy==2.3.0",
        "pydantic==2.13.4",
        "fastapi",
        "httpx",
        "hypothesis",
    )
)
for _item in _INCLUDE:
    _local = REPO_ROOT / _item
    if _local.exists():
        _remote = f"{REMOTE_ROOT}/{_item}"
        image = image.add_local_dir(str(_local), _remote) if _local.is_dir() \
            else image.add_local_file(str(_local), _remote)

app = modal.App("criba-hardening", image=image)

# Resources kept modest; the suite is tiny. Timeout generous but bounded.
_KW = dict(cpu=2.0, memory=4096, timeout=900)


def _run(cmd: list[str]) -> int:
    """Run a command in the container, stream output, return exit code."""
    import subprocess
    import sys

    env = {
        "PYTHONPATH": f"{REMOTE_ROOT}/src",
        "MYPYPATH": f"{REMOTE_ROOT}/src",
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    print(f"[cloud] $ {' '.join(cmd)}", flush=True)
    proc = subprocess.run(
        cmd,
        cwd=REMOTE_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    print(f"[cloud] exit_code={proc.returncode}", flush=True)
    return proc.returncode


@app.function(**_KW)
def _pytest_full() -> int:
    return _run([
        "python", "-m", "pytest", "-p", "no:cacheprovider", "-q",
        "--timeout=60", "--timeout-method=thread", f"{REMOTE_ROOT}/tests",
    ])


@app.function(**_KW)
def _pytest_file(path: str) -> int:
    return _run([
        "python", "-m", "pytest", "-p", "no:cacheprovider", "-v",
        "--timeout=30", "--timeout-method=thread", "-rA", f"{REMOTE_ROOT}/{path}",
    ])


@app.function(**_KW)
def _mypy_strict(target: str) -> int:
    return _run(["python", "-m", "mypy", "--strict", f"{REMOTE_ROOT}/{target}"])


@app.function(**_KW)
def _mypy_config() -> int:
    """Strict mypy using the project's [tool.mypy] config in pyproject.toml."""
    return _run(["python", "-m", "mypy", "src/criba"])


@app.function(**_KW)
def _coverage_run() -> int:
    return _run([
        "python", "-m", "pytest", "-p", "no:cacheprovider",
        "--cov=src/criba", "--cov-branch", "--cov-report=term-missing",
        "-q", f"{REMOTE_ROOT}/tests",
    ])


@app.function(**_KW)
def _benchmark_blackforge(repetitions: int) -> dict[str, object]:
    """Run the bounded benchmark remotely and return its JSON-safe report."""
    import sys

    sys.path.insert(0, REMOTE_ROOT)
    sys.path.insert(0, f"{REMOTE_ROOT}/src")
    from benchmarks.blackforge_benchmark import run_benchmark

    return run_benchmark(repetitions)


def _report_result(rc: int, label: str) -> None:
    """Print the remote result and propagate failures to the Modal CLI."""
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
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n=== RESULT rc=0 (benchmark -> {output_path}) ===")
