"""Smoke contract for the preserved v1 audit-intent engine."""
from __future__ import annotations

import pytest

from criba.constants import VALID_DECISIONS
from criba.engine_v1_audit_intent import activate, build_prompt


def test_v1_audit_engine_emits_serializable_business_decision() -> None:
    packet = activate(
        "Evaluar una alternativa reversible con evidencia",
        mode="minimal",
        supporting_methods=2,
    )

    decision = packet["decision"]
    assert decision["recommended_status"] in VALID_DECISIONS
    assert packet["original_query"] in build_prompt(packet)
    assert packet["packet_type"] == "MANDATORY_MODEL_PACKET"


def test_v1_audit_engine_rejects_empty_query() -> None:
    with pytest.raises(ValueError, match="vacia"):
        activate("   ")
