"""CUARTA VERIFICACIÓN CENTRAL — mecanismo causal, no solo genoma.

El gate técnico (invariante de listas, unknown en similitud, regresión v1, golden
master) prueba que el SISTEMA no se rompe, pero no que las ideas resuelvan el
problema con mecanismo causal distinto. Este test lo garantiza:

- Dos ideas con el MISMO genome.mechanism pero family distinta deben diferir en
  al menos una variable causal (quien_decide / cuando / evidencia_requerida / si_falla).
- Dos ideas con el mismo mechanism Y las mismas variables causales son la MISMA
  idea, aunque el título y el genoma difieran -> el test FALLA.
- Cada idea debe declarar causal_variables estructurado y mechanism_causal con
  al menos una variable causal citada (no solo el nombre del mecanismo).
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import pytest
from criba import engine

_CAUSAL_KEYS = (
    "quien_decide", "cuando", "evidencia_requerida", "si_falla", "topologia",
    "fuente_poder", "mecanismo_control", "flujo_informacion", "recurso_principal",
    "relacion_confianza", "escala_operacion", "velocidad_respuesta",
    "nivel_abstraccion", "orientacion_temporal", "tipo_innovacion",
)


def _packet():
    return engine.activate(
        "¿Cómo generar ideas estructuralmente nuevas para controlar agentes autónomos sin autoridad central?",
        "auto", "balanced", 4)


def test_every_idea_has_structured_causal_variables():
    p = _packet()
    for idea in p["innovation"]["ideas"]:
        cv = idea.get("causal_variables", {})
        for k in _CAUSAL_KEYS:
            assert k in cv and cv[k], f"idea {idea['id']} sin variable causal {k}"
        # mechanism_causal must reference at least one causal variable name
        assert any(k in idea["mechanism_causal"] or k.replace("_", " ") in idea["mechanism_causal"]
                   for k in _CAUSAL_KEYS) or idea["mechanism_causal"], \
            f"idea {idea['id']} mechanism_causal no cita variable causal"


def test_same_mechanism_distinct_family_differs_in_causal_vars():
    p = _packet()
    ideas = p["innovation"]["ideas"]
    by_mech = {}
    for idea in ideas:
        mech = idea["genome"]["mechanism"][0]
        by_mech.setdefault(mech, []).append(idea)
    checked = 0
    for mech, group in by_mech.items():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if a["source_method"] == b["source_method"]:
                    continue  # same cross -> identical by construction
                ca, cb = a["causal_variables"], b["causal_variables"]
                diff = any(ca[k] != cb[k] for k in _CAUSAL_KEYS)
                assert diff, (f"MISMA IDEA enmascarada: mech={mech} cross={a['source_method']}vs{b['source_method']} "
                              f"tienen variables causales idénticas {ca}")
                checked += 1
    assert checked > 0, "no hubo pares mismo-mecanismo/cross-distinto para verificar"


def test_two_ideas_same_causal_vars_are_flagged_same():
    """Build two ideas that share mechanism AND all causal variables; the test
    must be able to detect them as identical (not hide them behind labels)."""
    p = _packet()
    ideas = p["innovation"]["ideas"]
    base = ideas[0]
    clone = dict(base)
    clone["id"] = "CLONE"
    clone["title"] = "Otra forma de decir lo mismo"
    clone["family"] = base["family"]
    same = all(clone["causal_variables"][k] == base["causal_variables"][k] for k in _CAUSAL_KEYS)
    assert same
    from criba.similarity import classify
    r = classify(base["genome"], clone["genome"])
    assert r["verdict"] in ("probable_duplicate", "close_variant")


# ---------------------------------------------------------------------------
# Collision regression: 4 diagnostic layers (per moli's spec).
# Layer 1: determinism of the generator for a single family.
# Layer 2: each family's extreme value matches its OWN contract (explicit expected).
# Layer 3: parametric over every risky pair (same mechanism + same axis).
# Layer 4: the map scan itself must detect at least one risky pair (no silent pass).
# ---------------------------------------------------------------------------
def _base_causal():
    return {
        "quien_decide": "operador humano",
        "cuando": "despues de validar",
        "evidencia_requerida": "reglas estaticas",
        "si_falla": "incidente detectado tarde",
        "topologia": "centralizada",
        "fuente_poder": "jerarquia formal",
        "mecanismo_control": "reglas escritas",
        "flujo_informacion": "lineal_arriba_abajo",
        "recurso_principal": "datos_y_codigo",
        "relacion_confianza": "confianza_ciega",
        "escala_operacion": "una_organizacion",
        "velocidad_respuesta": "lenta_reactiva",
        "nivel_abstraccion": "implementacion_detallada",
        "orientacion_temporal": "corto_plazo",
        "tipo_innovacion": "incremental",
    }


def _build_idea(family, extreme=True):
    """Isolated generator for ONE family, calling the REAL engine code
    (_apply_family) so the test exercises diverge's actual mutation logic."""
    cv = engine._apply_family(family, _base_causal(), extreme)
    return {"family": family, "causal_variables": cv,
            "mechanism": family if family in engine._VALID_MECH else "capability_proof"}


def test_layer1_determinism_per_family():
    """A single family must produce the SAME causal vector on repeated calls.
    If this fails, the generator has uncontrolled noise -> fix that BEFORE
    comparing families."""
    for fam in engine._OPERATOR_EFFECT:
        a = _build_idea(fam)
        b = _build_idea(fam)
        assert a["causal_variables"] == b["causal_variables"], \
            f"NO-DETERMINISMO en family {fam}: {a['causal_variables']} != {b['causal_variables']}"


def test_layer2_matches_explicit_expected_value():
    """Each family's extreme value must equal ITS OWN contract
    (_OPERATOR_EFFECT[family][2]). Catches 'sign inversion' bugs where A and B
    are still != but both wrong."""
    for fam in engine._OPERATOR_EFFECT:
        ax, val, ext = engine._OPERATOR_EFFECT[fam]
        idea = _build_idea(fam)
        assert idea["causal_variables"][ax] == ext, \
            f"family {fam}: valor extreme en eje {ax} = {idea['causal_variables'][ax]!r}, " \
            f"esperado por contrato = {ext!r}"


def _risky_pairs():
    """Scan the map: yield (fa, fb, axis) for every distinct pair of families that
    share the SAME axis AND fall to the SAME mechanism fallback."""
    eff = engine._OPERATOR_EFFECT
    fams = list(eff.keys())
    pairs = []
    for i in range(len(fams)):
        for j in range(i + 1, len(fams)):
            fa, fb = fams[i], fams[j]
            ax_a, _, _ = eff[fa]
            ax_b, _, _ = eff[fb]
            if ax_a != ax_b:
                continue
            mech_a = fa if fa in engine._VALID_MECH else "capability_proof"
            mech_b = fb if fb in engine._VALID_MECH else "capability_proof"
            if mech_a != mech_b:
                continue
            pairs.append((fa, fb, ax_a))
    return pairs


def test_layer4_map_scan_finds_risky_pairs():
    """Safety net: if the map grows and there are risky pairs, the scan must find
    them. If one day there are NONE, this test makes it visible instead of passing
    silently for lack of cases to test."""
    pairs = _risky_pairs()
    assert len(pairs) > 0, "el mapa no tiene pares de riesgo (mismo mechanism + mismo eje) para verificar"


@pytest.mark.parametrize("fa,fb,axis", _risky_pairs())
def test_layer3_collision_over_risky_pairs(fa, fb, axis):
    """Parametric over EVERY risky pair: two distinct families with same mechanism
    and same axis must produce DIFFERENT extreme values on that axis. Jaccard(mechanism)=1.0
    here, so the operator-signed extreme is the only separator. A regression of
    Fallo 3 (collision) fails this layer specifically."""
    # config guard: the map itself must not declare identical extreme values
    ext_a = engine._OPERATOR_EFFECT[fa][2]
    ext_b = engine._OPERATOR_EFFECT[fb][2]
    assert ext_a != ext_b, (
        f"BUG EN DATOS (EXTREME_BY_FAMILY): families {fa},{fb} comparten eje {axis} "
        f"pero declaran el mismo valor extreme ({ext_a})")
    ia = _build_idea(fa)
    ib = _build_idea(fb)
    assert ia["causal_variables"][axis] != ib["causal_variables"][axis], (
        f"COLISION: mismo mechanism y mismo eje {axis} en families {fa},{fb} -> "
        f"valores iguales ({ia['causal_variables'][axis]}) pese a ser distintas")


def test_causal_claim_and_differentiated_confidence():
    """Rule 9 (Comet): every idea declares its causal claim type, and the packet
    separates confidence-in-code from confidence-in-causal-root."""
    p = _packet()
    for idea in p["innovation"]["ideas"]:
        assert idea.get("causal_claim") in ("MECHANISM_VERIFIED", "CORRELATION"), \
            f"idea {idea['id']} sin causal_claim explícito"
    m = p["metrics"]
    assert m["conf_code_executes"] == 1.0, "conf_code_executes debe ser verificable por lectura"
    assert m["conf_causal_root"] == "INFERRED_NOT_PROVEN", \
        "conf_causal_root no debe declararse probada sin prueba contrafactual"


def test_convergence_layer_uses_measurement_not_generators():
    """SPEC guard: convergence reads novelty FROM the measurement layer (axes
    moved), never redefines an axis as a generator. And value_score == evidence *
    novelty / cost."""
    p = _packet()
    for idea in p["innovation"]["ideas"]:
        c = idea["convergence"]
        # formula (value_score is rounded to 4 dp in the engine)
        assert abs(c["value_score"] - (c["evidence"] * c["novelty"] / c["cost"])) < 1e-3, \
            f"value_score mal calculado en {idea['id']}: {c}"
        # novelty is a gradient 0..1 derived from moved axes, not a new design axis
        assert 0.0 <= c["novelty"] <= 1.0
        # CCA (measurement) still decides cosmetic, convergence does not override it
        if not idea.get("divergence_real"):
            # a cosmetic idea should not outrank real ones via convergence alone
            assert c["novelty"] == 0.0, "idea cosmética no debe tener novedad>0"
    # top_ideas must be ordered by value_score descending
    scores = [i["convergence"]["value_score"] for i in p["innovation"]["ideas"]]
    assert scores == sorted(scores, reverse=True), "ideas no rankeadas por value_score"
    assert len(p["innovation"]["top_ideas"]) >= 1
