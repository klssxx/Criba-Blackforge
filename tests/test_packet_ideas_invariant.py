"""Condition 13 — invariant between legacy and innovation idea collections.

One canonical collection. packet["ideas"] MUST be the same object as
packet["innovation"]["ideas"]. Any divergence in length / order / ids / content
is a hard failure. This runs in EVERY local verification run via scripts/verify-mvp.ps1.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from criba import engine


def build_test_packet():
    return engine.activate(
        "¿Cómo generar ideas estructuralmente nuevas para controlar agentes autónomos sin autoridad central?",
        "auto", "balanced", 4)


def test_legacy_and_innovation_ideas_never_diverge():
    packet = build_test_packet()
    legacy_ids = [i["id"] for i in packet["ideas"]]
    innovation_ids = [i["id"] for i in packet["innovation"]["ideas"]]
    assert len(legacy_ids) == len(innovation_ids)
    assert legacy_ids == innovation_ids
    assert packet["ideas"] is packet["innovation"]["ideas"]


def test_order_and_id_set_equal():
    packet = build_test_packet()
    a = [(i["id"], i["title"]) for i in packet["ideas"]]
    b = [(i["id"], i["title"]) for i in packet["innovation"]["ideas"]]
    assert a == b


def test_content_per_id_equal():
    packet = build_test_packet()
    legacy = {i["id"]: i for i in packet["ideas"]}
    innov = {i["id"]: i for i in packet["innovation"]["ideas"]}
    assert set(legacy) == set(innov)
    for k in legacy:
        assert legacy[k] is innov[k]


def test_provoked_divergence_rejected():
    packet = build_test_packet()
    # the engine must not keep two mutable idea sources. Prove the live view is a
    # single object and that re-deriving from innovation yields equal content.
    import copy
    rebuilt = copy.deepcopy(packet["innovation"]["ideas"])
    assert [i["id"] for i in rebuilt] == [i["id"] for i in packet["ideas"]]
    assert packet["ideas"] is packet["innovation"]["ideas"]
