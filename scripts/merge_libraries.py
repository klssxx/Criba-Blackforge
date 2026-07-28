#!/usr/bin/env python3
"""
Fusiona la librería existente de CRIBA con los nuevos catálogos de ee/.
Genera library_combined.json como la fuente unificada de métodos.
"""

import json
from pathlib import Path
from typing import List, Dict, Any

METHODS_DIR = Path(r"E:\PROYECTS\CRIBA\data\methods")


def load_json(filepath: Path) -> List[Dict[str, Any]]:
    """Carga un archivo JSON."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filepath: Path, data: List[Dict[str, Any]]):
    """Guarda un archivo JSON."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_family(family: str) -> str:
    """Normaliza el nombre de la familia a un formato estándar."""
    family_lower = family.lower().strip()
    
    # Mapeo de familias normalizadas
    family_map = {
        "inversion": "inversion",
        "inversión": "inversion",
        "sustraccion": "sustraccion",
        "sustracción": "sustraccion",
        "recombinacion": "recombinacion",
        "recombinación": "recombinacion",
        "analogias": "analogias",
        "analogía": "analogias",
        "contraste": "contraste",
        "morfologia": "morfologia",
        "morfología": "morfologia",
        "temporalidad": "temporalidad",
        "actores_roles": "actores_roles",
        "restricciones": "restricciones",
        "complejidad": "complejidad",
        "decision_riesgo": "decision_riesgo",
        "decisión_riesgo": "decision_riesgo",
        "verificacion": "verificacion",
        "verificación": "verificacion",
        "diseno_adversarial": "diseno_adversarial",
        "diseño_adversarial": "diseno_adversarial",
        "gobernanza": "gobernanza",
        "prototipado": "prototipado",
        "narrativa": "narrativa",
        "identidad": "identidad",
        "redes": "redes",
        "simulacion": "simulacion",
        "simulación": "simulacion",
        "meta_cognicion": "meta_cognicion",
        "meta-cognición": "meta_cognicion",
        "incentivos": "incentivos",
        "comunicacion": "comunicacion",
        "comunicación": "comunicacion",
        "percepcion": "percepcion",
        "percepción": "percepcion",
        "modelado": "modelado",
        "sintesis": "sintesis",
        "síntesis": "sintesis",
        "divergencia": "divergencia",
        "optimizacion": "optimizacion",
        "optimización": "optimizacion",
        "resiliencia": "resiliencia",
        "aprendizaje": "aprendizaje",
        "cooperacion": "cooperacion",
        "cooperación": "cooperacion",
        "etica": "etica",
        "ética": "etica",
        "estetica": "estetica",
        "estética": "estetica",
        "economia": "economia",
        "economía": "economia",
        "seguridad": "seguridad",
        "escalabilidad": "escalabilidad",
        "sostenibilidad": "sostenibilidad",
        "velocidad": "velocidad",
        "precision": "precision",
        "precisión": "precision",
        "cobertura": "cobertura",
        "simplicidad": "simplicidad",
        "ruptura_marco": "ruptura_marco",
        "salto_espacio": "salto_espacio",
        "general": "general",
        "lente_avanzado": "lente_avanzado",
        "perspectiva": "perspectiva",
        "ciencia_realidad": "ciencia_realidad",
        "filosofia": "filosofia",
        "filosofía": "filosofia",
        "psicologia": "psicologia",
        "psicología": "psicologia",
        "estrategia": "estrategia",
        "creacion_diseno": "creacion_diseno",
        "creación_diseno": "creacion_diseno",
        "historia_culturas": "historia_culturas",
        "politica_poder": "politica_poder",
        "política_poder": "politica_poder",
        "naturaleza": "naturaleza",
        "tecnologia": "tecnologia",
        "tecnología": "tecnologia",
        "cuerpo_salud": "cuerpo_salud",
        "espacio_arquitectura": "espacio_arquitectura",
        "tiempo_memoria": "tiempo_memoria",
        "relacion_cuidado": "relacion_cuidado",
        "relación_cuidado": "relacion_cuidado",
        "trabajo_proceso": "trabajo_proceso",
        "sistemas_flujos": "sistemas_flujos",
        "riesgo_incertidumbre": "riesgo_incertidumbre",
        "muerte_trascendencia": "muerte_trascendencia",
        "juego_festival": "juego_festival",
        "soledad_silencio": "soledad_silencio",
        "escala_proporcion": "escala_proporcion",
        "sentido_humor": "sentido_humor",
        "imposible_prohibido": "imposible_prohibido",
        "cotidiano_domestico": "cotidiano_domestico",
        "colectivo_masivo": "colectivo_masivo",
        "fragmentario_incompleto": "fragmentario_incompleto",
        "exacto_preciso": "exacto_preciso",
        "aproximado_borroso": "aproximado_borroso",
        "estatico_permanente": "estatico_permanente",
        "dinamico_cambiante": "dinamico_cambiante",
        "simple_elemental": "simple_elemental",
        "complejo_multifacético": "complejo_multifacético",
        "visible_evidente": "visible_evidente",
        "oculto_secreto": "oculto_secreto",
        "bello_armonioso": "bello_armonioso",
        "feo_desordenado": "feo_desordenado",
        "util_funcional": "util_funcional",
        "util_ludico": "util_ludico",
        "verdadero_autentico": "verdadero_autentico",
        "falso_simulado": "falso_simulado",
        "bueno_justo": "bueno_justo",
        "malo_injusto": "malo_injusto",
        "sagrado_ritual": "sagrado_ritual",
        "profano_mundano": "profano_mundano",
    }
    
    return family_map.get(family_lower, family_lower)


def merge_libraries():
    """Fusiona las librerías existente y nueva."""
    print("Cargando librerías...")
    
    # Cargar librería existente
    existing_file = METHODS_DIR / "library_expanded.json"
    if existing_file.exists():
        existing = load_json(existing_file)
        print(f"  Librería existente: {len(existing)} métodos")
    else:
        existing = []
        print("  No se encontró librería existente")
    
    # Cargar nuevos catálogos
    ee_file = METHODS_DIR / "library_ee_expanded.json"
    if ee_file.exists():
        ee_methods = load_json(ee_file)
        print(f"  Catálogos ee/: {len(ee_methods)} métodos")
    else:
        ee_methods = []
        print("  No se encontró library_ee_expanded.json")
    
    # Normalizar familias en ambos conjuntos
    for m in existing:
        m["family"] = normalize_family(m.get("family", "general"))
    
    for m in ee_methods:
        m["family"] = normalize_family(m.get("family", "general"))
    
    # Combinar: existentes primero, luego nuevos
    combined = existing + ee_methods
    
    # Eliminar duplicados por ID (mantener el primero)
    seen_ids = set()
    unique_combined = []
    for m in combined:
        if m["id"] not in seen_ids:
            seen_ids.add(m["id"])
            unique_combined.append(m)
    
    print(f"\nTotal combinado: {len(unique_combined)} métodos únicos")
    
    # Estadísticas
    sources = {}
    for m in unique_combined:
        src = m.get("source", "original")
        sources[src] = sources.get(src, 0) + 1
    
    print("\nPor fuente:")
    for src, count in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"  {src}: {count}")
    
    families = {}
    for m in unique_combined:
        fam = m["family"]
        families[fam] = families.get(fam, 0) + 1
    
    print(f"\nTotal de familias: {len(families)}")
    print("Top 15 familias:")
    for fam, count in sorted(families.items(), key=lambda x: -x[1])[:15]:
        print(f"  {fam}: {count}")
    
    # Guardar librería combinada
    output_file = METHODS_DIR / "library_combined.json"
    save_json(output_file, unique_combined)
    print(f"\nGuardado en: {output_file}")
    
    return unique_combined


def main():
    combined = merge_libraries()
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE INTEGRACIÓN")
    print("=" * 60)
    print(f"Total de métodos: {len(combined)}")
    print(f"Familias únicas: {len(set(m['family'] for m in combined))}")
    print(f"Fuentes: {len(set(m.get('source', 'original') for m in combined))}")


if __name__ == "__main__":
    main()
