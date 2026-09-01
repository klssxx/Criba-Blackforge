from criba.engine import activate, build_prompt
from criba.methods import select_methods
from criba.selector import select

QUERY="¿Cómo podríamos diseñar un sistema de aprobación para agentes de programación que sea seguro sin depender de una autoridad central permanente?"
def test_selection_is_deterministic():
    assert select(QUERY)==select(QUERY)
def test_selector_is_explainable_and_bounded():
    result=select(QUERY); assert 0<=result["score"]<=100; assert result["selection_reasons"]; assert len(result["rejected_currents"])==11
def test_method_families_are_unique():
    items=select_methods(4,"strict"); assert len({x["family"] for x in items})==4
def test_packet_and_prompt_contract():
    packet=activate(QUERY); assert packet["packet_type"]=="MANDATORY_MODEL_PACKET"; assert len(packet["supporting_methods"])==12; assert packet["decision"]["recommended_status"]=="AMPLIAR PRUEBA"; assert "cadena de pensamiento privada" in build_prompt(packet)
def test_rejects_empty_and_oversized():
    import pytest
    with pytest.raises(ValueError): activate("")
    with pytest.raises(ValueError): activate("x"*20001)
def test_minimal(): assert "minimal_summary" in activate(QUERY,mode="minimal")

