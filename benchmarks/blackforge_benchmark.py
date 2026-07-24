"""Measure the real 723-record BLACKFORGE pipeline in Modal cloud.

The benchmark is intentionally small and sequential: one warm-up followed by at
most three measured repetitions per operation. It reports raw samples, median,
and nearest-rank p95 without enforcing fragile wall-clock pass/fail thresholds.
"""
from __future__ import annotations

import gc
import hashlib
import math
import os
import platform
import resource
import statistics
import sys
import time
from types import MappingProxyType
from typing import Any, Callable

from criba import blackforge_catalog as catalog
from criba.blackforge_causal import build_causal_signature
from criba.blackforge_pipeline import run_headless
from criba.blackforge_safety import evaluate_blackforge_safety
from criba.blackforge_selector import select_blackforge


_MODEL: dict[str, Any] = {
    "model_id": "BENCHMARK-PROBLEM-001",
    "schema_version": "1.0.0",
    "variables": [
        {
            "id": "CV-001",
            "axis": "decision_owner",
            "baseline_value": "central_authority",
            "allowed_values": ["central_authority", "distributed_quorum", "rule_engine"],
        },
        {
            "id": "CV-002",
            "axis": "failure_default",
            "baseline_value": "fail_closed",
            "allowed_values": ["fail_closed", "isolate", "rollback"],
        },
    ],
    "outcomes": [
        {"id": "OUT-001", "allowed_directions": ["increase", "decrease", "maintain"]},
    ],
}
_PROPOSAL: dict[str, Any] = {
    "proposal_id": "BENCHMARK-PROPOSAL-001",
    "primary_intervention": {
        "variable_id": "CV-001",
        "operation": "replace",
        "from": "central_authority",
        "to": "distributed_quorum",
    },
    "interventions": [
        {
            "variable_id": "CV-001",
            "operation": "replace",
            "from": "central_authority",
            "to": "distributed_quorum",
        },
        {
            "variable_id": "CV-002",
            "operation": "replace",
            "from": "fail_closed",
            "to": "isolate",
        },
    ],
    "affected_outcomes": [{"outcome_id": "OUT-001", "direction": "decrease"}],
}


def _measure(operation: Callable[[], Any], repetitions: int) -> dict[str, Any]:
    """Warm once, then measure sequential repetitions and release each result."""
    warmup_result = operation()
    del warmup_result
    gc.collect()

    samples_ms: list[float] = []
    for _ in range(repetitions):
        started = time.perf_counter_ns()
        result = operation()
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
        samples_ms.append(round(elapsed_ms, 6))
        del result
        gc.collect()

    ordered = sorted(samples_ms)
    p95_index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return {
        "repetitions": repetitions,
        "samples_ms": samples_ms,
        "median_ms": round(statistics.median(samples_ms), 6),
        "p95_nearest_rank_ms": ordered[p95_index],
    }


def run_benchmark(repetitions: int = 3) -> dict[str, Any]:
    """Run bounded benchmarks against the canonical BLACKFORGE catalog."""
    if not 1 <= repetitions <= 3:
        raise ValueError("repetitions must be between 1 and 3")

    catalog.reset_cache()
    _, records = catalog.load()
    if len(records) != 723:
        raise RuntimeError(f"expected 723 catalog records, found {len(records)}")

    selection = select_blackforge(seed=1, session_size=12, profile="hybrid")
    if not selection.status_ok() or len(selection.selected_ids) != 12:
        raise RuntimeError("canonical selector did not produce the expected 12-item session")
    selected_ids = tuple(selection.selected_ids)
    selected_records = tuple(catalog.get(item_id) for item_id in selected_ids)
    if any(item is None for item in selected_records):
        raise RuntimeError("selector returned an ID absent from the canonical catalog")

    def cold_catalog_load() -> int:
        catalog.reset_cache()
        _, loaded_records = catalog.load()
        return len(loaded_records)

    def construct_id_index() -> int:
        _, loaded_records = catalog.load()
        index = MappingProxyType({str(item["blackforge_id"]): item for item in loaded_records})
        return len(index)

    def lookup_selected_ids() -> tuple[Any, ...]:
        return tuple(catalog.get(item_id) for item_id in selected_ids)

    def select_session() -> dict[str, Any]:
        return select_blackforge(seed=1, session_size=12, profile="hybrid").to_dict()

    def safety_gate() -> tuple[str, ...]:
        decisions = (
            evaluate_blackforge_safety(item, {}, clock=lambda: 0.0, session_id="benchmark")
            for item in selected_records
            if item is not None
        )
        return tuple(decision.decision for decision in decisions)

    def causal_signature() -> str:
        return str(build_causal_signature(_PROPOSAL, _MODEL)["digest"])

    def headless_pipeline() -> dict[str, Any]:
        return run_headless(seed=1, session_size=12, session_id="benchmark")

    catalog_bytes = catalog._CATALOG_PATH.read_bytes()
    operations = {
        "catalog_cold_load_validate_freeze": _measure(cold_catalog_load, repetitions),
        "catalog_id_index_construction": _measure(construct_id_index, repetitions),
        "catalog_lookup_12_selected_ids": _measure(lookup_selected_ids, repetitions),
        "selector": _measure(select_session, repetitions),
        "safety_gate_12_items": _measure(safety_gate, repetitions),
        "causal_signature_validation": _measure(causal_signature, repetitions),
        "headless_pipeline": _measure(headless_pipeline, repetitions),
    }
    slowest = max(operations, key=lambda name: operations[name]["median_ms"])

    return {
        "schema": "criba_blackforge_benchmark",
        "schema_version": "1.0.0",
        "methodology": {
            "warmup_per_operation": 1,
            "repetitions": repetitions,
            "execution": "sequential",
            "clock": "time.perf_counter_ns",
            "summary": "median and nearest-rank p95; no fragile timing gate",
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "cpu_count_visible": os.cpu_count(),
            "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "modal_resource_limits": {"cpu": 2.0, "memory_mib": 4096},
        },
        "input": {
            "catalog_records": len(records),
            "catalog_sha256": hashlib.sha256(catalog_bytes).hexdigest(),
            "catalog_bytes": len(catalog_bytes),
            "selector_seed": 1,
            "session_size": 12,
        },
        "operations": operations,
        "observed_slowest_operation_by_median": slowest,
    }
