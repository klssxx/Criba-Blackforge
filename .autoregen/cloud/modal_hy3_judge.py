from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import modal

LOCAL_ROOT = Path(__file__).resolve().parents[2]
REMOTE_ROOT = Path("/workspace")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install("httpx>=0.27", "jsonschema>=4.22")
    .workdir("/workspace")
    .add_local_dir(
        str(LOCAL_ROOT),
        remote_path="/workspace",
        ignore=[
            ".git/**", ".venv/**", "**/__pycache__/**", "artifacts/**",
            "*.db", "*.sqlite", "*.sqlite3", ".env", ".env.*",
        ],
    )
)

app = modal.App("criba-hy3-semantic-judge")


def _source_hash() -> str:
    digest = hashlib.sha256()
    for rel in [
        "src/criba/personas.py",
        "tests/unit/test_personas.py",
        "docs/phases/P2_PERSONA_SYSTEM_EXECUTABLE.md",
        ".autoregen/cloud/verification_manifest.json",
    ]:
        path = REMOTE_ROOT / rel
        if path.exists():
            digest.update(rel.encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _read(rel: str, limit: int = 180_000) -> str:
    path = REMOTE_ROOT / rel
    if not path.exists():
        return f"[MISSING: {rel}]"
    return path.read_text(encoding="utf-8", errors="replace")[:limit]


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("criba-openrouter", required_keys=["OPENROUTER_API_KEY"])],
    timeout=60 * 60,
)
def judge_p2() -> str:
    import httpx

    source_hash = _source_hash()
    schema = _read("schemas/hy3_review.schema.json")
    prompt = f"""
Audita P2 Persona System de CRIBA. Actúa como revisor adversarial, no como autor.
Devuelve EXCLUSIVAMENTE JSON válido conforme al schema incluido.
No inventes pruebas ni líneas. No declares VERIFIED con hallazgos BLOCKER/HIGH.
Comprueba separación real de personas, colapso parcial, preservación minoritaria,
aislamiento, autorización conservadora, scope P3-P10 y tests.

SOURCE_HASH: {source_hash}

SCHEMA:
{schema}

P2 SPEC:
{_read("docs/phases/P2_PERSONA_SYSTEM_EXECUTABLE.md")}

PERSONAS.PY:
{_read("src/criba/personas.py")}

TEST_PERSONAS.PY:
{_read("tests/unit/test_personas.py")}

MODAL RESULT:
{_read("artifacts/modal/latest-result.json")}
""".strip()

    response = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={
            "model": "tencent/hy3:free",
            "messages": [
                {
                    "role": "system",
                    "content": "Eres un auditor de software riguroso. Responde solo JSON válido."
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 12000,
        },
        timeout=3600,
    )
    response.raise_for_status()
    payload: dict[str, Any] = response.json()
    content = payload["choices"][0]["message"]["content"]
    return str(content)


@app.local_entrypoint()
def main(phase: str = "P2") -> None:
    if phase.upper() != "P2":
        raise SystemExit("This version only authorizes P2.")
    content = judge_p2.remote()
    output = LOCAL_ROOT / "artifacts" / "hy3" / "P2_REVIEW.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    print(content)
