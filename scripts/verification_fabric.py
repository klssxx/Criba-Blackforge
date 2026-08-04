"""Pure contracts and gate policy for the Modal Verification Fabric.

This module deliberately has no Modal dependency.  The cloud adapter lives in
``.autoregen/cloud/modal_runner.py``; keeping policy here makes the manifest,
hashing, and automatic verdict independently testable.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Final, Literal, Mapping, Sequence


FABRIC_SCHEMA_VERSION: Final[str] = "1.0.0"
MANIFEST_HASH_FIELD: Final[str] = "manifest_sha256"
GateStatus = Literal["passed", "failed", "error"]
FabricVerdict = Literal["PASS", "FAIL", "ERROR"]

FROZEN_TOOLCHAIN: Final[dict[str, str]] = {
    "python": "3.12",
    "pytest": "9.1.1",
    "pytest-cov": "7.1.0",
    "pytest-timeout": "2.4.0",
    "coverage": "7.15.1",
    "mypy": "2.3.0",
    "pydantic": "2.13.4",
    "fastapi": "0.140.0",
    "httpx": "0.28.1",
    "hypothesis": "6.161.1",
    "ruff": "0.12.12",
    "mutmut": "3.6.0",
}


@dataclass(frozen=True)
class GateSpec:
    """One independent, bounded verification input."""

    gate_id: str
    category: str
    command: tuple[str, ...]
    required: bool = True
    command_timeout_seconds: int = 900
    artifact_paths: tuple[str, ...] = ()
    minimum_coverage_percent: float | None = None
    minimum_mutation_score: float | None = None

    def __post_init__(self) -> None:
        if not self.gate_id or not self.category:
            raise ValueError("gate_id and category must be non-empty")
        if not self.command:
            raise ValueError(f"{self.gate_id}: command must be non-empty")
        if not 1 <= self.command_timeout_seconds <= 86_400:
            raise ValueError(f"{self.gate_id}: timeout must be between 1 second and 24 hours")
        for value, label in (
            (self.minimum_coverage_percent, "minimum_coverage_percent"),
            (self.minimum_mutation_score, "minimum_mutation_score"),
        ):
            if value is not None and not 0.0 <= value <= 100.0:
                raise ValueError(f"{self.gate_id}: {label} must be in [0, 100]")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe transport representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> GateSpec:
        """Validate a transport representation at the worker boundary."""
        return cls(
            gate_id=_required_string(value, "gate_id"),
            category=_required_string(value, "category"),
            command=tuple(_string_sequence(value, "command")),
            required=bool(value.get("required", True)),
            command_timeout_seconds=int(value.get("command_timeout_seconds", 900)),
            artifact_paths=tuple(_string_sequence(value, "artifact_paths")),
            minimum_coverage_percent=_optional_float(value.get("minimum_coverage_percent")),
            minimum_mutation_score=_optional_float(value.get("minimum_mutation_score")),
        )


@dataclass(frozen=True)
class GateResult:
    """Structured result returned by one Modal map input."""

    gate_id: str
    category: str
    required: bool
    status: GateStatus
    return_code: int
    duration_seconds: float
    command: tuple[str, ...]
    stdout: str
    stderr: str
    metrics: Mapping[str, float] = field(default_factory=dict)
    artifacts: tuple[Mapping[str, Any], ...] = ()
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe result with tamper-evident log hashes."""
        value = asdict(self)
        value["stdout_sha256"] = sha256_text(self.stdout)
        value["stderr_sha256"] = sha256_text(self.stderr)
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> GateResult:
        """Validate a worker result before verdict calculation."""
        raw_metrics = value.get("metrics", {})
        metrics = (
            {str(key): float(metric) for key, metric in raw_metrics.items()}
            if isinstance(raw_metrics, Mapping)
            else {}
        )
        raw_artifacts = value.get("artifacts", ())
        artifacts = (
            tuple(dict(item) for item in raw_artifacts if isinstance(item, Mapping))
            if isinstance(raw_artifacts, Sequence) and not isinstance(raw_artifacts, (str, bytes))
            else ()
        )
        status = str(value.get("status", "error"))
        if status not in {"passed", "failed", "error"}:
            raise ValueError(f"invalid gate status: {status!r}")
        return cls(
            gate_id=_required_string(value, "gate_id"),
            category=_required_string(value, "category"),
            required=bool(value.get("required", True)),
            status=status,  # type: ignore[arg-type]
            return_code=int(value.get("return_code", -1)),
            duration_seconds=float(value.get("duration_seconds", 0.0)),
            command=tuple(_string_sequence(value, "command")),
            stdout=str(value.get("stdout", "")),
            stderr=str(value.get("stderr", "")),
            metrics=metrics,
            artifacts=artifacts,
            error=str(value["error"]) if value.get("error") is not None else None,
        )


def p2_gate_specs() -> list[GateSpec]:
    """Build the complete P2 profile executed through ``Function.map``."""
    persona_tests = (
        "tests/unit/test_personas.py",
        "tests/property/test_personas_properties.py",
        "tests/adversarial/test_personas_adversarial.py",
    )
    pytest_base = (
        "python",
        "-m",
        "pytest",
        "-p",
        "no:cacheprovider",
        "--timeout=60",
        "--timeout-method=thread",
    )
    mutation_targets = (
        ("mutation_persona_c", "criba.personas.x__parse_persona_output__mutmut_*"),
        ("mutation_run_persona", "criba.personas.x_run_persona__mutmut_*"),
        (
            "mutation_diversity",
            "criba.personas.x_evaluate_persona_diversity__mutmut_*",
        ),
        ("mutation_protocol", "criba.personas.x_validate_team_protocol__mutmut_*"),
        (
            "mutation_authorization",
            "criba.personas.x__authorization_status__mutmut_*",
        ),
    )
    specs = [
        GateSpec(
            gate_id="p2_unit",
            category="unit",
            command=pytest_base
            + ("-q", persona_tests[0], "--junitxml={artifact_dir}/p2-unit.xml"),
            artifact_paths=("p2-unit.xml",),
        ),
        GateSpec(
            gate_id="p2_adversarial",
            category="adversarial",
            command=pytest_base
            + ("-q", persona_tests[2], "--junitxml={artifact_dir}/p2-adversarial.xml"),
            artifact_paths=("p2-adversarial.xml",),
        ),
        GateSpec(
            gate_id="p2_property",
            category="property",
            command=pytest_base
            + (
                "-q",
                "--hypothesis-seed=4444",
                persona_tests[1],
                "--junitxml={artifact_dir}/p2-property.xml",
            ),
            artifact_paths=("p2-property.xml",),
        ),
        GateSpec(
            gate_id="p2_coverage",
            category="coverage",
            command=pytest_base
            + (
                "-q",
                *persona_tests,
                "--cov=criba.personas",
                "--cov-branch",
                "--cov-report=term-missing",
                "--cov-report=xml:{artifact_dir}/p2-coverage.xml",
                "--cov-fail-under=85",
            ),
            artifact_paths=("p2-coverage.xml",),
            minimum_coverage_percent=85.0,
        ),
        GateSpec(
            gate_id="p2_mypy",
            category="typing",
            command=("python", "-m", "mypy", "--strict", "src/criba/personas.py"),
        ),
        GateSpec(
            gate_id="p2_lint",
            category="lint",
            command=(
                "python",
                "-m",
                "ruff",
                "check",
                "src/criba/personas.py",
                *persona_tests,
                "scripts/verification_fabric.py",
                "scripts/verify_persona_determinism.py",
                "scripts/run_mutation_gate.py",
            ),
        ),
        GateSpec(
            gate_id="p2_determinism",
            category="determinism",
            command=(
                "python",
                "scripts/verify_persona_determinism.py",
                "--repetitions",
                "5",
                "--output",
                "{artifact_dir}/p2-determinism.json",
            ),
            artifact_paths=("p2-determinism.json",),
        ),
        GateSpec(
            gate_id="regression_full",
            category="regression",
            command=pytest_base
            + ("-q", "tests", "--junitxml={artifact_dir}/regression-full.xml"),
            command_timeout_seconds=1_800,
            artifact_paths=("regression-full.xml",),
        ),
    ]
    specs.extend(
        GateSpec(
            gate_id=gate_id,
            category="mutation",
            command=(
                "python",
                "scripts/run_mutation_gate.py",
                "--target",
                target,
                "--minimum-score",
                "80",
                "--output",
                f"{{artifact_dir}}/{gate_id}.json",
            ),
            command_timeout_seconds=7_200,
            artifact_paths=(f"{gate_id}.json",),
            minimum_mutation_score=80.0,
        )
        for gate_id, target in mutation_targets
    )
    return specs


def profile_gate_specs(profile: str) -> list[GateSpec]:
    """Return a named fabric profile without silently widening its scope."""
    if profile == "p2":
        return p2_gate_specs()
    raise ValueError(f"unknown verification profile: {profile!r}")


def automatic_verdict(
    specs: Sequence[GateSpec],
    results: Sequence[GateResult],
) -> tuple[FabricVerdict, list[str]]:
    """Evaluate required gates, completeness, and quantitative thresholds."""
    expected = {spec.gate_id: spec for spec in specs}
    observed: dict[str, GateResult] = {}
    reasons: list[str] = []
    for result in results:
        if result.gate_id in observed:
            reasons.append(f"duplicate result: {result.gate_id}")
        observed[result.gate_id] = result

    missing = sorted(set(expected) - set(observed))
    unexpected = sorted(set(observed) - set(expected))
    reasons.extend(f"missing result: {gate_id}" for gate_id in missing)
    reasons.extend(f"unexpected result: {gate_id}" for gate_id in unexpected)

    has_error = False
    for gate_id, spec in expected.items():
        result = observed.get(gate_id)
        if result is None:
            has_error = True
            continue
        if result.status == "error":
            has_error = True
            reasons.append(f"{gate_id}: infrastructure error")
        elif spec.required and result.status != "passed":
            reasons.append(f"{gate_id}: required gate {result.status}")

        if spec.minimum_coverage_percent is not None:
            actual = result.metrics.get("coverage_percent")
            if actual is None:
                has_error = True
                reasons.append(f"{gate_id}: coverage metric missing")
            elif actual < spec.minimum_coverage_percent:
                reasons.append(
                    f"{gate_id}: coverage {actual:.2f}% < {spec.minimum_coverage_percent:.2f}%"
                )
        if spec.minimum_mutation_score is not None:
            actual = result.metrics.get("mutation_score")
            if actual is None:
                has_error = True
                reasons.append(f"{gate_id}: mutation score missing")
            elif actual < spec.minimum_mutation_score:
                reasons.append(
                    f"{gate_id}: mutation score {actual:.2f}% < "
                    f"{spec.minimum_mutation_score:.2f}%"
                )

    if has_error:
        return "ERROR", reasons
    if reasons:
        return "FAIL", reasons
    return "PASS", []


def build_source_snapshot(root: Path, includes: Sequence[str]) -> dict[str, Any]:
    """Hash the exact local inputs copied into the Modal image."""
    entries: list[dict[str, Any]] = []
    for include in sorted(set(includes)):
        candidate = root / include
        if not candidate.exists():
            continue
        files = [candidate] if candidate.is_file() else sorted(candidate.rglob("*"))
        for path in files:
            if not path.is_file() or _ignored_snapshot_path(path):
                continue
            relative = path.relative_to(root).as_posix()
            entries.append(
                {
                    "path": relative,
                    "size": path.stat().st_size,
                    "sha256": sha256_bytes(path.read_bytes()),
                }
            )
    digest = sha256_text(canonical_json(entries))
    return {"sha256": digest, "file_count": len(entries), "files": entries}


def build_manifest(
    *,
    run_id: str,
    profile: str,
    source_snapshot: Mapping[str, Any],
    specs: Sequence[GateSpec],
    results: Sequence[GateResult],
    created_at_utc: str,
    execution: Mapping[str, Any],
) -> dict[str, Any]:
    """Create a self-hashed, machine-verifiable fabric manifest."""
    verdict, reasons = automatic_verdict(specs, results)
    manifest: dict[str, Any] = {
        "schema_version": FABRIC_SCHEMA_VERSION,
        "run_id": run_id,
        "profile": profile,
        "created_at_utc": created_at_utc,
        "toolchain": dict(FROZEN_TOOLCHAIN),
        "source_snapshot": dict(source_snapshot),
        "execution": dict(execution),
        "gates": [spec.to_dict() for spec in specs],
        "results": [result.to_dict() for result in results],
        "verdict": verdict,
        "verdict_reasons": reasons,
    }
    manifest[MANIFEST_HASH_FIELD] = manifest_sha256(manifest)
    return manifest


def manifest_sha256(manifest: Mapping[str, Any]) -> str:
    """Hash canonical manifest content while excluding the self-hash field."""
    unsigned = {str(key): value for key, value in manifest.items() if key != MANIFEST_HASH_FIELD}
    return sha256_text(canonical_json(unsigned))


def verify_manifest(manifest: Mapping[str, Any]) -> tuple[bool, str]:
    """Validate schema, self-hash, gate completeness, and stored log hashes."""
    if manifest.get("schema_version") != FABRIC_SCHEMA_VERSION:
        return False, "unsupported schema_version"
    expected_hash = manifest.get(MANIFEST_HASH_FIELD)
    if not isinstance(expected_hash, str) or expected_hash != manifest_sha256(manifest):
        return False, "manifest_sha256 mismatch"

    raw_specs = manifest.get("gates")
    raw_results = manifest.get("results")
    if not isinstance(raw_specs, list) or not isinstance(raw_results, list):
        return False, "gates/results must be lists"
    try:
        specs = [GateSpec.from_dict(value) for value in raw_specs if isinstance(value, Mapping)]
        results = [GateResult.from_dict(value) for value in raw_results if isinstance(value, Mapping)]
    except (TypeError, ValueError) as exc:
        return False, f"invalid gate data: {exc}"
    if len(specs) != len(raw_specs) or len(results) != len(raw_results):
        return False, "non-object gate/result entry"

    for raw, result in zip(raw_results, results):
        if raw.get("stdout_sha256") != sha256_text(result.stdout):
            return False, f"{result.gate_id}: stdout_sha256 mismatch"
        if raw.get("stderr_sha256") != sha256_text(result.stderr):
            return False, f"{result.gate_id}: stderr_sha256 mismatch"

    verdict, reasons = automatic_verdict(specs, results)
    if manifest.get("verdict") != verdict or manifest.get("verdict_reasons") != reasons:
        return False, "stored verdict does not match automatic verdict"
    return True, "manifest verified"


def canonical_json(value: Any) -> str:
    """Serialize JSON deterministically for content-addressed evidence."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_bytes(value: bytes) -> str:
    """Return a lowercase SHA-256 digest."""
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    """Hash UTF-8 text."""
    return sha256_bytes(value.encode("utf-8"))


def _required_string(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise ValueError(f"{key} must be a non-empty string")
    return item


def _string_sequence(value: Mapping[str, Any], key: str) -> list[str]:
    raw = value.get(key, ())
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError(f"{key} must be a sequence of strings")
    items = [str(item) for item in raw]
    if any(not item for item in items):
        raise ValueError(f"{key} must not contain empty values")
    return items


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _ignored_snapshot_path(path: Path) -> bool:
    ignored_parts = {
        ".git",
        ".venv",
        ".mypy_cache",
        ".pytest_cache",
        "__pycache__",
        "artifacts",
        "dist",
        "build",
        "compose_run",
        "lottery_results",
    }
    return path.suffix.casefold() == ".bak" or any(
        part in ignored_parts for part in path.parts
    )
