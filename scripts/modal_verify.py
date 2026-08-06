"""Run the portable CRIBA verification gates in an isolated Modal container."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import modal

LOCAL_ROOT = Path(__file__).resolve().parents[1]
REMOTE_ROOT = "/repo"


def _ignore_upload(path: Path) -> bool:
    return bool({".git", ".venv", "build", "dist", "artifacts"} & set(path.parts))


image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install(
        "libdbus-1-3",
        "libegl1",
        "libfontconfig1",
        "libgl1",
        "libglib2.0-0",
        "libx11-xcb1",
        "libxcb-cursor0",
        "libxcb-icccm4",
        "libxcb-keysyms1",
        "libxcb-render-util0",
        "libxcb-shape0",
        "libxcb-xinerama0",
        "libxkbcommon-x11-0",
        "libxi6",
        "libxrender1",
    )
    .pip_install("uv==0.11.28")
    .env({"QT_QPA_PLATFORM": "offscreen"})
    .add_local_dir(LOCAL_ROOT, REMOTE_ROOT, copy=True, ignore=_ignore_upload)
)
app = modal.App("criba-blackforge-verify", image=image)


def _run(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=REMOTE_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "command": command,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


@app.function(timeout=1_200, cpu=4, memory=8192)
def verify() -> dict[str, Any]:
    checks = [
        _run(["uv", "sync", "--all-extras", "--locked"]),
        _run(["uv", "run", "pytest", "-q"]),
        _run(["uv", "run", "mypy", "src/criba"]),
        _run(
            [
                "uv",
                "run",
                "ruff",
                "check",
                "--select",
                "E9,F63,F7,F82",
                "src/criba",
                "tests",
                "scripts",
                ".autoregen/cloud/modal_runner.py",
            ]
        ),
        _run(["uv", "run", "python", "scripts/verify_library.py"]),
    ]
    return {
        "passed": all(check["exit_code"] == 0 for check in checks),
        "checks": checks,
    }


@app.local_entrypoint()
def main() -> None:
    result = verify.remote()
    output = LOCAL_ROOT / "artifacts" / "modal_verification.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["passed"]:
        raise SystemExit(1)
