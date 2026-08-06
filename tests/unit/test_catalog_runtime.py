"""Runtime catalog composition and provenance contracts."""

from __future__ import annotations

from collections import Counter

from criba.catalog import methods


def test_runtime_catalog_loads_every_approved_source_without_id_collisions() -> None:
    catalog = methods()
    ids = [str(item["id"]) for item in catalog]

    assert len(catalog) == 7_201
    assert len(ids) == len(set(ids))

    sources = Counter(str(item.get("source")) for item in catalog)
    assert sources["escape_1030_master"] == 30
    assert sources["foundational_methods"] == 66
    assert (
        sum(
            sources[name]
            for name in (
                "brainstorming_techniques",
                "decision_frameworks",
                "gamestorming",
                "ideo_method_cards",
                "incident_response",
                "innovation_frameworks",
                "liberating_structures",
                "pentest_methodologies",
                "red_team_playbooks",
                "research_taxonomies",
                "security_frameworks",
            )
        )
        == 235
    )


def test_master_escape_extension_is_exact_and_traceable() -> None:
    extension = [
        item for item in methods() if item.get("source") == "escape_1030_master"
    ]

    assert [item["source_number"] for item in extension] == list(range(1001, 1031))
    assert [item["id"] for item in extension] == [
        f"escape_master_{number:04d}" for number in range(1001, 1031)
    ]
    assert all(item.get("source_ref") for item in extension)
    assert all(
        "FIN DEL CATÁLOGO" not in str(item.get("template")) for item in extension
    )


def test_foundational_records_receive_runtime_provenance_defaults() -> None:
    foundational = [
        item for item in methods() if item.get("source") == "foundational_methods"
    ]

    assert len(foundational) == 66
    assert all(item.get("granularity") == "method" for item in foundational)
    assert all(item.get("origin") == "internal" for item in foundational)
