#!/usr/bin/env python3
"""
Parsea los catálogos de metodologías de la carpeta ee/ y los convierte
al formato JSON utilizado por CRIBA BLACKFORGE.

Archivos de entrada:
- 800_metodos_ideas_disruptivas.txt
- 1000_tecnicas_ruptura_de_marco.txt
- 800_tecnicas_salto_espacio_conocido.txt
- 1700 puntos de vista.txt
- lentes_1101-1700.txt

Salida: data/methods/library_ee_expanded.json
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Any

EE_DIR = Path(r"C:\Users\KLSX\Downloads\ee")
OUTPUT_DIR = Path(r"E:\PROYECTS\CRIBA\data\methods")


def parse_800_metodos(filepath: Path) -> List[Dict[str, Any]]:
    """Parsea 800_metodos_ideas_disruptivas.txt"""
    methods = []
    current_family = ""
    family_map = {
        "Inversión estructural": "inversion",
        "Eliminación y sustracción": "sustraccion",
        "Combinación y recombinación": "recombinacion",
        "Analogía y trasplante": "analogias",
        "Contraste y paradoja": "contraste",
        "Escalado y distorsión": "morfologia",
        "Temporalidad y secuencia": "temporalidad",
        "Role reversal y perspectiva": "actores_roles",
        "Restricciones y presiones": "restricciones",
        "Emergencia y complejidad": "complejidad",
        "Decisión y riesgo": "decision_riesgo",
        "Medición y verificación": "verificacion",
        "Diseño adversarial": "diseno_adversarial",
        "Gobernanza y control": "gobernanza",
        "Prototipado y experimentación": "prototipado",
        "Narrativa y significado": "narrativa",
        "Identidad y transformación": "identidad",
        "Redes y distribución": "redes",
        "Simulación y juego": "simulacion",
        "Meta-cognición y reflexión": "meta_cognicion",
        "Incentivos y motivación": "incentivos",
        "Comunicación y lenguaje": "comunicacion",
        "Observación y percepción": "percepcion",
        "Abstracción y modelado": "modelado",
        "Síntesis y convergencia": "sintesis",
        "Divergencia y exploracion": "divergencia",
        "Optimización y eficiencia": "optimizacion",
        "Robustez y resiliencia": "resiliencia",
        "Adaptación y aprendizaje": "aprendizaje",
        "Cooperación y competencia": "cooperacion",
        "Ética y valores": "etica",
        "Estética y forma": "estetica",
        "Economía y valor": "economia",
        "Privacidad y seguridad": "seguridad",
        "Escalabilidad y crecimiento": "escalabilidad",
        "Sostenibilidad y durabilidad": "sostenibilidad",
        "Velocidad y latencia": "velocidad",
        "Precisión y exactitud": "precision",
        "Cobertura y completitud": "cobertura",
        "Simplicidad y claridad": "simplicidad",
    }
    
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    method_id = 1
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Detectar cabecera de familia (línea que termina con "--------")
        if line.endswith("-" * 5) and len(line) > 10:
            current_family = line.rstrip("-").strip()
            continue
        
        # Detectar líneas de método: "N. Nombre — Descripción"
        match = re.match(r"^(\d+)\.\s+(.+?)\s*[—–-]\s*(.+)$", line)
        if match:
            num, name, description = match.groups()
            family_key = family_map.get(current_family, "general")
            
            methods.append({
                "id": f"EE800-{int(num):04d}",
                "name": name.strip(),
                "family": family_key,
                "source": "800_metodos_ideas_disruptivas",
                "source_number": int(num),
                "selection_reason": description.strip(),
                "template": f"Aplicar el método '{name.strip()}' al problema planteado.",
                "category": current_family,
            })
            method_id += 1
    
    return methods


def parse_1000_tecnicas(filepath: Path) -> List[Dict[str, Any]]:
    """Parsea 1000_tecnicas_ruptura_de_marco.txt"""
    methods = []
    current_section = ""
    section_map = {
        "Inversión estructural": "inversion",
        "Eliminación y sustracción": "sustraccion",
        "Combinación y recombinación": "recombinacion",
        "Analogía y trasplante": "analogias",
        "Contraste y paradoja": "contraste",
        "Escalado y distorsión": "morfologia",
        "Temporalidad y secuencia": "temporalidad",
        "Role reversal y perspectiva": "actores_roles",
        "Restricciones y presiones": "restricciones",
        "Emergencia y complejidad": "complejidad",
        "Decisión y riesgo": "decision_riesgo",
        "Medición y verificación": "verificacion",
        "Diseño adversarial": "diseno_adversarial",
        "Gobernanza y control": "gobernanza",
        "Prototipado y experimentación": "prototipado",
        "Narrativa y significado": "narrativa",
        "Identidad y transformación": "identidad",
        "Redes y distribución": "redes",
        "Simulación y juego": "simulacion",
        "Meta-cognición y reflexión": "meta_cognicion",
        "Incentivos y motivación": "incentivos",
        "Comunicación y lenguaje": "comunicacion",
        "Observación y percepción": "percepcion",
        "Abstracción y modelado": "modelado",
        "Síntesis y convergencia": "sintesis",
        "Divergencia y exploracion": "divergencia",
        "Optimización y eficiencia": "optimizacion",
        "Robustez y resiliencia": "resiliencia",
        "Adaptación y aprendizaje": "aprendizaje",
        "Cooperación y competencia": "cooperacion",
        "Ética y valores": "etica",
        "Estética y forma": "estetica",
        "Economía y valor": "economia",
        "Privacidad y seguridad": "seguridad",
        "Escalabilidad y crecimiento": "escalabilidad",
        "Sostenibilidad y durabilidad": "sostenibilidad",
        "Velocidad y latencia": "velocidad",
        "Precisión y exactitud": "precision",
        "Cobertura y completitud": "cobertura",
        "Simplicidad y claridad": "simplicidad",
    }
    
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Detectar cabecera de sección (romanos)
        if re.match(r"^[IVX]+\.\s+", line):
            current_section = re.sub(r"^[IVX]+\.\s+", "", line).strip()
            continue
        
        # Detectar técnica: "N. Nombre — Descripción"
        match = re.match(r"^(\d+)\.\s+(.+?)\s*[—–-]\s*(.+)$", line)
        if match:
            num, name, description = match.groups()
            family_key = section_map.get(current_section, "ruptura_marco")
            
            methods.append({
                "id": f"EE1K-{int(num):04d}",
                "name": name.strip(),
                "family": family_key,
                "source": "1000_tecnicas_ruptura_de_marco",
                "source_number": int(num),
                "selection_reason": description.strip(),
                "template": f"Aplicar la técnica de ruptura '{name.strip()}' al marco actual.",
                "category": current_section,
            })
    
    return methods


def parse_800_salto(filepath: Path) -> List[Dict[str, Any]]:
    """Parsea 800_tecnicas_salto_espacio_conocido.txt"""
    methods = []
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Buscar patrones: "N. Nombre — Descripción" o "N. Nombre: Descripción"
    patterns = [
        re.finditer(r"(\d+)\.\s+(.+?)\s*[—–:]\s*(.+?)(?=\n\n|\n\d+\.|$)", content, re.DOTALL),
        re.finditer(r"(\d+)\.\s+(.+?)\s*[—–]\s*(.+?)(?=\n\n|\n\d+\.|$)", content, re.DOTALL),
    ]
    
    seen_ids = set()
    method_id = 1
    
    for pattern in patterns:
        for match in pattern:
            num, name, description = match.groups()
            name = name.strip()
            desc = description.strip().replace("\n", " ")
            
            if num not in seen_ids:
                seen_ids.add(num)
                methods.append({
                    "id": f"EE800S-{int(num):04d}",
                    "name": name,
                    "family": "salto_espacio",
                    "source": "800_tecnicas_salto_espacio_conocido",
                    "source_number": int(num),
                    "selection_reason": desc,
                    "template": f"Aplicar la técnica de salto '{name}' para salir del espacio conocido.",
                    "category": "salto_espacio_conocido",
                })
                method_id += 1
    
    return methods


def parse_1700_puntos(filepath: Path) -> List[Dict[str, Any]]:
    """Parsea 1700 puntos de vista.txt"""
    methods = []
    current_category = ""
    
    category_map = {
        "Conocimiento, ciencia y realidad": "ciencia_realidad",
        "Conocimiento, ciencia y realidad": "ciencia_realidad",
        "Filosofía y existencia": "filosofia",
        "Mente, psicología y comportamiento": "psicologia",
        "Cultura, sociedad y poder": "cultura_sociedad",
        "Tecnología,信息 y sistemas": "tecnologia",
        "Naturaleza, vida y evolución": "naturaleza",
        "Tiempo, causalidad y cambio": "tiempo_causalidad",
        "Identidad, moral y significado": "identidad_moral",
        "Lo desconocido, lo oculto y lo especulativo": "desconocido",
        "Economía, incentivos y juegos": "economia_juegos",
        "Arte, percepción y forma": "arte_percepcion",
    }
    
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Detectar cabecera de categoría
        if re.match(r"^\d+\.\s+[A-ZÁÉÍÓÚ]", line) and "Lente" not in line:
            current_category = re.sub(r"^\d+\.\s+", "", line).strip()
            continue
        
        # Detectar lente: "Lente X: Descripción"
        match = re.match(r"Lente\s+(.+?):\s*(.+)$", line, re.IGNORECASE)
        if match:
            name, description = match.groups()
            cat_key = category_map.get(current_category, "perspectiva")
            
            methods.append({
                "id": f"EE1700-{len(methods)+1:04d}",
                "name": f"Lente {name.strip()}",
                "family": cat_key,
                "source": "1700_puntos_de_vista",
                "source_number": len(methods) + 1,
                "selection_reason": description.strip(),
                "template": f"Observar el problema desde la perspectiva de '{name.strip()}'.",
                "category": current_category,
            })
    
    return methods


def parse_lentes_1101(filepath: Path) -> List[Dict[str, Any]]:
    """Parsea lentes_1101-1700.txt"""
    methods = []
    
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Detectar lente: "NNNN. Lente del X: Descripción"
        match = re.match(r"^(\d+)\.\s+Lente\s+(?:del|de la|de los|de las)\s+(.+?):\s*(.+)$", line, re.IGNORECASE)
        if match:
            num, name, description = match.groups()
            methods.append({
                "id": f"EE1101-{int(num):04d}",
                "name": f"Lente {name.strip()}",
                "family": "lente_avanzado",
                "source": "lentes_1101-1700",
                "source_number": int(num),
                "selection_reason": description.strip(),
                "template": f"Observar el problema desde la perspectiva de '{name.strip()}'.",
                "category": "lentes_avanzados",
            })
    
    return methods


def main():
    print("Parseando catálogos de la carpeta ee/...")
    
    all_methods = []
    
    # Parsear cada archivo
    files_to_parse = [
        ("800_metodos_ideas_disruptivas.txt", parse_800_metodos),
        ("1000_tecnicas_ruptura_de_marco.txt", parse_1000_tecnicas),
        ("800_tecnicas_salto_espacio_conocido.txt", parse_800_salto),
        ("1700 puntos de vista.txt", parse_1700_puntos),
        ("lentes_1101-1700.txt", parse_lentes_1101),
    ]
    
    for filename, parser_func in files_to_parse:
        filepath = EE_DIR / filename
        if filepath.exists():
            print(f"Parseando {filename}...")
            methods = parser_func(filepath)
            print(f"  -> {len(methods)} métodos extraídos")
            all_methods.extend(methods)
        else:
            print(f"  -> Archivo no encontrado: {filename}")
    
    print(f"\nTotal de métodos extraídos: {len(all_methods)}")
    
    # Guardar resultado
    output_file = OUTPUT_DIR / "library_ee_expanded.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_methods, f, ensure_ascii=False, indent=2)
    
    print(f"Guardado en: {output_file}")
    
    # Estadísticas por fuente
    sources = {}
    for m in all_methods:
        src = m["source"]
        sources[src] = sources.get(src, 0) + 1
    
    print("\nEstadísticas por fuente:")
    for src, count in sorted(sources.items()):
        print(f"  {src}: {count}")
    
    # Estadísticas por familia
    families = {}
    for m in all_methods:
        fam = m["family"]
        families[fam] = families.get(fam, 0) + 1
    
    print("\nEstadísticas por familia:")
    for fam, count in sorted(families.items(), key=lambda x: -x[1])[:20]:
        print(f"  {fam}: {count}")


if __name__ == "__main__":
    main()
