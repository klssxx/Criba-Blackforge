"""Tests for manifest integrity and automatic fabric gates."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from scripts.verification_fabric import (
    FABRIC_SCHEMA_VERSION,
    FROZEN_TOOLCHAIN,
    GateResult,
    GateSpec,
    automatic_verdict,
    build_manifest,
    build_source_snapshot,
    canonical_json,
    p2_gate_specs,
    verify_manifest,
)


def test_modal_image_pin_matches_declared_mutmut_toolchain() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    modal_runner = (repo_root / ".autoregen/cloud/modal_runner.py").read_text(
        encoding="utf-8"
    )
    expected_pin = f'"mutmut=={FROZEN_TOOLCHAIN["mutmut"]}"'
    assert expected_pin in modal_runner


def _result(spec: GateSpec, **changes: object) -> GateResult:
    result = GateResult(
        gate_id=spec.gate_id,
        category=spec.category,
        required=spec.required,
        status="passed",
        return_code=0,
        duration_seconds=1.0,
        command=spec.command,
        stdout="ok",
        stderr="",
        metrics={},
    )
    return replace(result, **changes)


def test_p2_profile_covers_requested_verification_categories() -> None:
    specs = p2_gate_specs()
    categories = {spec.category for spec in specs}
    assert {
        "unit",
        "adversarial",
        "property",
        "coverage",
        "typing",
        "lint",
        "determinism",
        "mutation",
        "regression",
    } <= categories
    assert len(specs) == len({spec.gate_id for spec in specs})
    assert all(spec.command_timeout_seconds <= 86_400 for spec in specs)
    mutation_targets = {
        spec.command[spec.command.index("--target") + 1]
        for spec in specs
        if spec.category == "mutation"
    }
    assert mutation_targets == {
        "criba.personas.x__parse_persona_output__mutmut_*",
        "criba.personas.x_run_persona__mutmut_*",
        "criba.personas.x_evaluate_persona_diversity__mutmut_*",
        "criba.personas.x_validate_team_protocol__mutmut_*",
        "criba.personas.x__authorization_status__mutmut_*",
    }


def test_required_failure_produces_fail() -> None:
    spec = GateSpec("unit", "unit", ("python", "-m", "pytest"))
    verdict, reasons = automatic_verdict(
        [spec],
        [_result(spec, status="failed", return_code=1)],
    )
    assert verdict == "FAIL"
    assert reasons == ["unit: required gate failed"]


def test_missing_result_or_metric_is_infrastructure_error() -> None:
    coverage = GateSpec(
        "coverage",
        "coverage",
        ("coverage", "run"),
        minimum_coverage_percent=90.0,
    )
    verdict, reasons = automatic_verdict([coverage], [_result(coverage)])
    assert verdict == "ERROR"
    assert "coverage: coverage metric missing" in reasons

    verdict, reasons = automatic_verdict([coverage], [])
    assert verdict == "ERROR"
    assert "missing result: coverage" in reasons


def test_quantitative_thresholds_are_enforced() -> None:
    mutation = GateSpec(
        "mutation",
        "mutation",
        ("mutmut", "run"),
        minimum_mutation_score=80.0,
    )
    verdict, reasons = automatic_verdict(
        [mutation],
        [_result(mutation, metrics={"mutation_score": 79.99})],
    )
    assert verdict == "FAIL"
    assert reasons == ["mutation: mutation score 79.99% < 80.00%"]


def test_manifest_self_hash_and_log_hash_detect_tampering(tmp_path: Path) -> None:
    spec = GateSpec("unit", "unit", ("python", "-m", "pytest"))
    result = _result(spec)
    manifest = build_manifest(
        run_id="vf-test",
        profile="p2",
        source_snapshot=build_source_snapshot(tmp_path, ()),
        specs=[spec],
        results=[result],
        created_at_utc="2026-07-26T00:00:00Z",
        execution={"provider": "modal", "map": True},
    )
    assert manifest["schema_version"] == FABRIC_SCHEMA_VERSION
    assert verify_manifest(manifest) == (True, "manifest verified")
    # JSON round-trip must preserve integrity: serialize the manifest, parse it
    # back, and require the reconstructed document to still verify against its own
    # embedded manifest_sha256. This proves the canonical hash survives a full
    # serialize/deserialize cycle. (The previous form compared
    # json.dumps(manifest) against itself, which was tautological and proved
    # nothing about round-trip fidelity or hash stability.)
    round_tripped = json.loads(json.dumps(manifest, ensure_ascii=False))
    assert verify_manifest(round_tripped) == (True, "manifest verified")
    # Round-trip stability must be checked on the JSON-normalized form, not the
    # raw Python object: GateSpec.command is a tuple internally, but the manifest
    # is a JSON document where command serializes to list[str]. The same
    # canonical_json used by manifest_sha256/verify_manifest is the contract.
    assert canonical_json(manifest) == canonical_json(json.loads(json.dumps(manifest)))

    tampered = json.loads(json.dumps(manifest))
    tampered["results"][0]["stdout"] = "forged"
    assert verify_manifest(tampered) == (False, "manifest_sha256 mismatch")


def test_source_snapshot_excludes_backups_and_generated_verification_runs(
    tmp_path: Path,
) -> None:
    source = tmp_path / "src" / "criba"
    source.mkdir(parents=True)
    (source / "engine.py").write_text("ACTIVE = True\n", encoding="utf-8")
    (source / "engine.py.bak").write_text("stale backup\n", encoding="utf-8")

    verification = tmp_path / "verification"
    (verification / "compose_run").mkdir(parents=True)
    (verification / "lottery_results").mkdir(parents=True)
    (verification / "canonical.json").write_text("{}\n", encoding="utf-8")
    (verification / "compose_run" / "scratch.json").write_text(
        "{}\n", encoding="utf-8"
    )
    (verification / "lottery_results" / "generated.json").write_text(
        "{}\n", encoding="utf-8"
    )

    snapshot = build_source_snapshot(tmp_path, ("src", "verification"))

    assert [entry["path"] for entry in snapshot["files"]] == [
        "src/criba/engine.py",
        "verification/canonical.json",
    ]


def test_gate_rejects_timeout_beyond_modal_limit() -> None:
    with pytest.raises(ValueError, match="24 hours"):
        GateSpec(
            "too-long",
            "stress",
            ("python", "stress.py"),
            command_timeout_seconds=86_401,
        )
