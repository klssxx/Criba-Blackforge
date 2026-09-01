"""Property-based invariants for the isolated P2 persona layer."""
from __future__ import annotations

import copy

from hypothesis import given, settings
from hypothesis import strategies as st

from criba.personas import (
    PERSONA_IDS,
    PersonaD,
    PersonaResult,
    build_persona_prompt,
    evaluate_persona_diversity,
    run_personas,
)

_safe_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)),
    min_size=1,
    max_size=160,
).filter(lambda value: bool(value.strip()))


@st.composite
def packets(draw: st.DrawFn) -> dict[str, object]:
    query = draw(_safe_text)
    known_space = draw(st.lists(_safe_text, max_size=4))
    assumptions = draw(st.lists(_safe_text, max_size=4))
    assets = draw(st.lists(_safe_text, max_size=4))
    authorization = draw(
        st.sampled_from(
            ["pending", "granted", "denied", "expired", "not_required", "unknown-value"]
        )
    )
    return {
        "original_query": query,
        "intent": "INNOVAR",
        "model_instruction": "No inventar evidencia.",
        "innovation": {
            "known_space": known_space,
            "assumptions": assumptions,
            "ruptures": [],
        },
        "protected_assets": assets,
        "authorization_state": authorization,
    }


@given(packets())
@settings(max_examples=40, deadline=None)
def test_fallback_is_deterministic_round_trippable_and_non_mutating(
    packet: dict[str, object],
) -> None:
    before = copy.deepcopy(packet)
    first = run_personas(packet)
    second = run_personas(packet)

    assert packet == before
    assert first == second
    assert [result.persona_id for result in first] == list(PERSONA_IDS)
    assert evaluate_persona_diversity(first).is_diverse
    for result in first:
        assert PersonaResult.model_validate_json(result.model_dump_json()) == result


@given(packets(), _safe_text)
@settings(max_examples=30, deadline=None)
def test_isolation_keys_never_reach_any_persona_prompt(
    packet: dict[str, object], secret: str
) -> None:
    # Wrap the injected secret in a collision-proof sentinel so the invariant
    # ("payloads placed only inside isolation-excluded keys never reach a persona
    # prompt") cannot produce a false positive when Hypothesis draws a secret that
    # happens to equal legitimate packet content (e.g. secret == original_query).
    # The sentinel prefix cannot appear in any legitimately-rendered packet field,
    # so its presence in a prompt would prove a real isolation leak.
    marker = f"__CRIBA_ISOLATION_SENTINEL__{secret}__"
    contaminated = packet | {
        "prior_persona_outputs": [{"private_marker": marker}],
        "persona_outputs": [{"private_marker": marker}],
        "ensemble_outputs": [{"private_marker": marker}],
    }
    for persona_id in PERSONA_IDS:
        prompt = build_persona_prompt(persona_id, contaminated)
        assert marker not in prompt
        assert "__CRIBA_ISOLATION_SENTINEL__" not in prompt


@given(packets())
@settings(max_examples=30, deadline=None)
def test_unknown_authorization_never_becomes_granted(packet: dict[str, object]) -> None:
    packet["authorization_state"] = "not-a-valid-authorization"
    result = run_personas(packet)[3]
    assert isinstance(result.output, PersonaD)
    assert result.output.authorization_status == "pending"
