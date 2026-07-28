#!/usr/bin/env python3
"""Regenera el golden master después de cambios en la librería de métodos."""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from criba import engine

QUERY = ("¿Cómo podemos generar ideas estructuralmente nuevas para controlar las acciones "
         "de agentes autónomos sin depender de una autoridad central permanente?")

p = engine.activate(QUERY, "auto", "balanced", 4)

# Remove non-deterministic fields
stable = {k: v for k, v in p.items() if k not in ("activation_id", "timestamp")}
stable = json.loads(json.dumps(stable, ensure_ascii=False, sort_keys=True))

# Save as new golden master
golden_path = os.path.join(os.path.dirname(__file__), "..", "tests", "golden_mvp_output.json")
with open(golden_path, "w", encoding="utf-8") as f:
    json.dump(stable, f, ensure_ascii=False, indent=2)

print("Golden master actualizado")
print(f"Metodos soporte: {len(p['supporting_methods'])}")
print(f"Ideas generadas: {len(p['innovation']['ideas'])}")
