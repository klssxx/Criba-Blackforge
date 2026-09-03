"""P05-T03 claim-store tests: isolated SQLite persistence and queries."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from criba.intelligence import contracts as C
from criba.intelligence.storage import IntelligenceStore


@pytest.fixture()
def store(tmp_path):
    instance = IntelligenceStore(tmp_path / "intelligence.sqlite3")
    yield instance
    instance.close()


def test_claim_roundtrip_decodes_json_and_ignores_contract_extras(store):
    claim = C.Claim(
        text="Cooling reduces energy use",
        epistemic_state=C.EpistemicState.FACT,
        evidence_doc_ids=("doc-1", "doc-2"),
        fragment_ids=("frag-1",),
        technique_ids=("T100",),
        created_by="rule",
    )
    payload = claim.to_dict() | {"run_id": "run-a", "unsupported": "ignored"}

    store.save_claim(payload)
    got = store.get_claim(claim.claim_id)

    assert got is not None
    assert got["claim_id"] == claim.claim_id
    assert got["run_id"] == "run-a"
    assert got["text"] == claim.text
    assert got["epistemic_state"] == "FACT"
    assert got["evidence_doc_ids"] == ["doc-1", "doc-2"]
    assert got["fragment_ids"] == ["frag-1"]
    assert got["technique_ids"] == ["T100"]
    assert "unsupported" not in got
    assert store.get_claim("missing") is None


def test_claim_list_filters_by_run_and_epistemic_state(store):
    fact = C.Claim(text="fact", epistemic_state=C.EpistemicState.FACT)
    inference = C.Claim(text="inference", epistemic_state=C.EpistemicState.INFERENCE)
    store.save_claim(fact.to_dict() | {"run_id": "run-a"})
    store.save_claim(inference.to_dict() | {"run_id": "run-b"})

    assert [item["claim_id"] for item in store.list_claims(run_id="run-a")] == [fact.claim_id]
    assert [item["claim_id"] for item in store.list_claims(
        epistemic_state=C.EpistemicState.INFERENCE
    )] == [inference.claim_id]
    assert len(store.list_claims(limit=1)) == 1


def test_claim_upsert_replaces_existing_record(store):
    claim = C.Claim(text="original")
    store.save_claim(claim.to_dict())
    store.save_claim(claim.to_dict() | {"text": "updated", "run_id": "run-a"})

    got = store.get_claim(claim.claim_id)
    assert got is not None
    assert got["text"] == "updated"
    assert got["run_id"] == "run-a"
    assert len(store.list_claims()) == 1


def test_claim_requires_identifier(store):
    with pytest.raises(KeyError, match="claim_id"):
        store.save_claim({"text": "invalid"})
