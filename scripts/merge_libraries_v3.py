#!/usr/bin/env python3
"""
Merge inteligente v3: Fusiona librería existente con 11 fuentes nuevas.
Enriquece schema con granularity, categories, tags, origin, related_internal_ids.
"""
import json
from pathlib import Path
from typing import Any

METHODS_DIR = Path(__file__).resolve().parents[1] / "data" / "methods"
ONTOLOGY_PATH = METHODS_DIR / "ontology.json"

# Defaults para campos nuevos en ítems existentes
DEFAULTS = {
    "granularity": "micro_technique",
    "categories": [],
    "tags": [],
    "origin": "internal",
    "external_refs": [],
    "related_internal_ids": [],
    "normalized_mechanism": "",
    "relationship_type": "",
}


def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_mechanism(item: dict) -> str:
    """Genera un normalized_mechanism si no existe."""
    if item.get("normalized_mechanism"):
        return item["normalized_mechanism"]
    name = item.get("name", "").lower().strip()
    # Extraer关键词 del nombre
    keywords = []
    for word in ["invertir", "eliminar", "combinar", "analizar", "detectar",
                 "prevenir", "mitigar", "evaluar", "priorizar", "diseñar",
                 "crear", "medir", "observar", "explorar", "identificar",
                 "modelar", "simular", "clasificar", "agrupar", "conectar"]:
        if word in name:
            keywords.append(word)
    return "_".join(keywords) if keywords else name.replace(" ", "_")[:40]


def build_source_index(new_items: list) -> dict:
    """Indexa nuevos ítems por ID para búsqueda rápida."""
    return {item["id"]: item for item in new_items}


def migrate_existing(item: dict) -> dict:
    """Migra un ítem existente al nuevo schema con defaults."""
    migrated = dict(item)
    for key, default in DEFAULTS.items():
        if key not in migrated:
            migrated[key] = default if not isinstance(default, list) else list(default)
    # Auto-categorizar basado en family
    if not migrated["categories"]:
        family = migrated.get("family", "general")
        family_to_cat = {
            "inversion": ["innovacion", "resolucion"],
            "sustraccion": ["innovacion", "resolucion"],
            "recombinacion": ["innovacion"],
            "analogias": ["innovacion", "investigacion"],
            "morfologia": ["innovacion", "diseno"],
            "restricciones": ["innovacion", "resolucion"],
            "actores_roles": ["innovacion", "facilitacion"],
            "diseno_adversarial": ["seguridad", "innovacion"],
            "verificacion": ["seguridad", "mejora"],
            "decision_riesgo": ["seguridad", "decision_riesgo"],
            "gobernanza": ["seguridad", "gobernanza"],
            "ruptura_marco": ["innovacion", "tecnicas_de_salto"],
            "salto_espacio": ["innovacion", "tecnicas_de_salto"],
            "lente_avanzado": ["puntos_de_vista"],
            "perspectiva": ["puntos_de_vista"],
            "ciencia_realidad": ["puntos_de_vista", "investigacion"],
            "filosofia": ["puntos_de_vista"],
            "psicologia": ["puntos_de_vista"],
            "estrategia": ["estrategia"],
            "economia": ["negocio"],
            "seguridad": ["seguridad"],
        }
        migrated["categories"] = family_to_cat.get(family, ["innovacion"])
    # Auto-tag desde name
    if not migrated["tags"]:
        name_lower = migrated.get("name", "").lower()
        tag_keywords = ["inversion", "eliminacion", "combinacion", "analogia",
                       "restriccion", "simulacion", "observacion", "deteccion",
                       "prevencion", "analisis", "diseno", "innovacion"]
        migrated["tags"] = [kw for kw in tag_keywords if kw in name_lower][:3]
    return migrated


def find_related(new_item: dict, all_existing: list, threshold: int = 2) -> list:
    """Encuentra ítems existentes relacionados con un ítem nuevo."""
    related = []
    new_name = new_item.get("name", "").lower()
    new_tags = set(new_item.get("tags", []))
    new_mechanism = new_item.get("normalized_mechanism", "")
    for ex in all_existing:
        score = 0
        ex_name = ex.get("name", "").lower()
        ex_tags = set(ex.get("tags", []))
        # Coincidencia por nombre
        if any(w in ex_name for w in new_name.split() if len(w) > 4):
            score += 2
        # Coincidencia por tags
        if new_tags & ex_tags:
            score += 1
        # Coincidencia por mechanism
        if new_mechanism and new_mechanism in ex.get("normalized_mechanism", ""):
            score += 2
        if score >= threshold:
            related.append(ex["id"])
    return related[:5]  # max 5 related


def detect_equivalences(items: list) -> list:
    """Detecta posibles equivalencias por normalized_mechanism."""
    mech_index = {}
    for item in items:
        mech = item.get("normalized_mechanism", "")
        if mech and len(mech) > 5:
            if mech not in mech_index:
                mech_index[mech] = []
            mech_index[mech].append(item["id"])
    # Marcar duplicados
    for item in items:
        mech = item.get("normalized_mechanism", "")
        if mech in mech_index and len(mech_index[mech]) > 1:
            if not item.get("relationship_type"):
                item["relationship_type"] = "equivalente"
    return items


def merge():
    print("=== MERGE LIBRARIES V3 ===\n")
    
    # 1. Cargar librería existente
    existing_path = METHODS_DIR / "library_combined.json"
    if existing_path.exists():
        existing = load_json(existing_path)
        print(f"Existing library: {len(existing)} items")
    else:
        existing = []
        print("No existing library found")
    
    # 2. Cargar todas las fuentes nuevas
    new_items = []
    source_files = sorted(METHODS_DIR.glob("source_*.json"))
    for sf in source_files:
        items = load_json(sf)
        print(f"  {sf.name}: {len(items)} items")
        new_items.extend(items)
    print(f"Total new items: {len(new_items)}")
    
    # 3. Migrar ítems existentes al nuevo schema
    print("\nMigrating existing items...")
    migrated = [migrate_existing(item) for item in existing]
    print(f"  Migrated: {len(migrated)} items")
    
    # 4. Indexar nuevos ítems
    new_index = build_source_index(new_items)
    
    # 5. Enriquecer nuevos ítems con related_internal_ids
    print("Building equivalence map...")
    for item in new_items:
        if not item.get("related_internal_ids"):
            item["related_internal_ids"] = find_related(item, migrated)
    
    # 6. Combinar
    combined = migrated + new_items
    print(f"\nCombined total: {len(combined)} items")
    
    # 7. Detectar equivalencias
    combined = detect_equivalences(combined)
    
    # 8. Eliminar duplicados por ID (mantener el primero)
    seen_ids = set()
    unique = []
    for item in combined:
        if item["id"] not in seen_ids:
            seen_ids.add(item["id"])
            unique.append(item)
    print(f"After dedup: {len(unique)} items")
    
    # 9. Estadísticas
    sources = {}
    granularities = {}
    for item in unique:
        src = item.get("source", "original")
        sources[src] = sources.get(src, 0) + 1
        gran = item.get("granularity", "micro_technique")
        granularities[gran] = granularities.get(gran, 0) + 1
    
    print("\nBy source:")
    for src, count in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"  {src}: {count}")
    
    print("\nBy granularity:")
    for gran, count in sorted(granularities.items(), key=lambda x: -x[1]):
        print(f"  {gran}: {count}")
    
    # 10. Guardar
    output = METHODS_DIR / "library_combined.json"
    save_json(output, unique)
    print(f"\nSaved to: {output}")
    print(f"Final count: {len(unique)}")


if __name__ == "__main__":
    merge()
