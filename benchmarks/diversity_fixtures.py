"""Fixtures deterministas compartidos por las mediciones PRE y POST de diversidad.

DV11 (megaprompt §64): exactamente los mismos fixtures antes y después del
cambio de selector. Sin red, sin aleatoriedad: candidatos con genoma completo
(mechanism/trust_model/topology/actor/time_model) y score controlado.

Estructura del genoma: la que consume criba.similarity (genome_distance/
classify). Los campos son listas multivalor o "unknown".
"""

ANTI_CONVERGENCE_POOL: list[dict] = [
    # A y A' y A'': casi el mismo candidato (duplicado probable) con scores altos.
    # B, C, D: estructuralmente distintos con scores algo menores.
    {"idea_id": "A", "score": 0.90, "family": "automatizacion",
     "methods": ["T014", "T057"],
     "genome": {"mechanism": ["orquestar-modelo-central"],
                "trust_model": ["centralizado"],
                "topology": ["hub-spoke"],
                "actor": ["operador-humano"],
                "time_model": ["tiempo-real"]}},
    {"idea_id": "A2", "score": 0.89, "family": "automatizacion",
     "methods": ["T014", "T057"],
     "genome": {"mechanism": ["orquestar-modelo-central"],
                "trust_model": ["centralizado"],
                "topology": ["hub-spoke"],
                "actor": ["operador-humano"],
                "time_model": ["tiempo-real"]}},
    {"idea_id": "A3", "score": 0.88, "family": "automatizacion",
     "methods": ["T014", "T088"],
     "genome": {"mechanism": ["orquestar-modelo-central"],
                "trust_model": ["centralizado"],
                "topology": ["hub-spoke"],
                "actor": ["supervisor"],
                "time_model": ["tiempo-real"]}},
    {"idea_id": "B", "score": 0.84, "family": "incentivos",
     "methods": ["T021", "T099"],
     "genome": {"mechanism": ["invertir-incentivos"],
                "trust_model": ["distribuido"],
                "topology": ["p2p"],
                "actor": ["comunidad"],
                "time_model": ["por-lotes"]}},
    {"idea_id": "C", "score": 0.80, "family": "sustraccion",
     "methods": ["T003", "T044"],
     "genome": {"mechanism": ["eliminar-restriccion-dominante"],
                "trust_model": ["sin-confianza"],
                "topology": ["malla"],
                "actor": ["auditor-externo"],
                "time_model": ["previo"]}},
    {"idea_id": "D", "score": 0.78, "family": "trasplante",
     "methods": ["T051", "T120"],
     "genome": {"mechanism": ["trasplantar-mecanismo-otro-dominio"],
                "trust_model": ["federado"],
                "topology": ["anillo"],
                "actor": ["algoritmo"],
                "time_model": ["continuo"]}},
]

# Pool con pares de métodos repetidos entre candidatos (mide reutilización).
PAIR_REUSE_POOL: list[dict] = [
    {"idea_id": "R1", "score": 0.91, "family": "f1", "methods": ["T001", "T002"],
     "genome": {"mechanism": ["m1"], "trust_model": ["t1"], "topology": ["x1"],
                "actor": ["a1"], "time_model": ["tt1"]}},
    {"idea_id": "R2", "score": 0.90, "family": "f1", "methods": ["T001", "T002"],
     "genome": {"mechanism": ["m1"], "trust_model": ["t1"], "topology": ["x2"],
                "actor": ["a1"], "time_model": ["tt2"]}},
    {"idea_id": "R3", "score": 0.85, "family": "f2", "methods": ["T010", "T011"],
     "genome": {"mechanism": ["m2"], "trust_model": ["t2"], "topology": ["x3"],
                "actor": ["a2"], "time_model": ["tt3"]}},
    {"idea_id": "R4", "score": 0.80, "family": "f3", "methods": ["T020", "T021"],
     "genome": {"mechanism": ["m3"], "trust_model": ["t3"], "topology": ["x4"],
                "actor": ["a3"], "time_model": ["tt4"]}},
]
