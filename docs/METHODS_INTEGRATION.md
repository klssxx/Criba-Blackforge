# Integración de Catálogos de Metodologías CRIBA BLACKFORGE

## Resumen

Librería unificada de **4002 métodos** de innovación, seguridad y hacking ético, organizados en **17 fuentes** y **5 granularidades**.

## Estadísticas Finales

| Métrica | Valor |
|---------|-------|
| Total de métodos | 4002 |
| Fuentes | 17 |
| Granularidades | 5 (micro_technique, framework, method, facilitation_pattern, group_game) |
| Frameworks | 111 |
| Métodos de diseño (IDEO) | 51 |
| Patrones de facilitación | 25 |
| Juegos de grupo | 19 |

## Fuentes

### Fuentes originales (ee/)
| Fuente | Ítems | Descripción |
|--------|-------|-------------|
| 1000_tecnicas_ruptura_de_marco | 1000 | Técnicas de ruptura de marco mental |
| 800_tecnicas_salto_espacio_conocido | 801 | Estrategias de salto fuera del espacio conocido |
| 800_metodos_ideas_disruptivas | 800 | Métodos para ideación disruptiva |
| 1700_puntos_de_vista | 550 | Lentes y perspectivas múltiples |
| lentes_1101-1700 | 550 | Lentes avanzados de decisión |
| original | 66 | Métodos base de CRIBA |

### Fuentes nuevas (frameworks meta-nivel)
| Fuente | Ítems | Granularidad | Descripción |
|--------|-------|--------------|-------------|
| innovation_frameworks | 35 | framework | Design Thinking, JTBD, Blue Ocean, FMEA, etc. |
| security_frameworks | 15 | framework | MITRE ATT&CK, OWASP, STRIDE, Kill Chain, etc. |
| pentest_methodologies | 12 | framework | PTES, OSSTMM, OWASP Testing, etc. |
| red_team_playbooks | 11 | framework | Red Team Ops, Purple Team, Atomic Red Team, etc. |
| incident_response | 11 | framework | NIST IR, SANS, Forensics, etc. |
| decision_frameworks | 14 | framework | RICE, Weighted Scoring, Delphi, Six Hats, etc. |
| research_taxonomies | 20 | framework | Experimental, Grounded Theory, Ethnography, etc. |
| ideo_method_cards | 51 | method | 51 métodos de design research (Ask/Look/Learn/Try) |
| liberating_structures | 25 | facilitation_pattern | 1-2-4-All, 9 Whys, Fishbowl, etc. |
| brainstorming_techniques | 22 | method | Brainwriting, SCAMPER, Synectics, Crazy 8s, etc. |
| gamestorming | 19 | group_game | Anti-Problem, Dot Voting, Mind Map, etc. |

## Granularidades

| Granularidad | Cantidad | Uso |
|--------------|----------|-----|
| micro_technique | 3767 | Técnicas atómicas para selección automática |
| framework | 111 | Marcos de referencia para orquestación |
| method | 80 | Métodos de investigación de diseño |
| facilitation_pattern | 25 | Patrones para sesiones grupales |
| group_game | 19 | Juegos de taller e innovación |

## Schema Enriquecido

Cada ítem tiene estos campos:

```json
{
  "id": "str (único global)",
  "name": "str",
  "family": "str (normalizada)",
  "selection_reason": "str",
  "template": "str",
  "source": "str (fuente original)",
  "granularity": "micro_technique|framework|method|facilitation_pattern|group_game",
  "categories": ["investigacion", "innovacion", "seguridad", ...],
  "tags": ["adversarial", "divergencia", ...],
  "origin": "internal|external",
  "normalized_mechanism": "str (para comparación semántica)",
  "related_internal_ids": ["ID1", "ID2", ...],
  "relationship_type": "equivalente|inspirado_en|complementa|..."
}
```

## Uso en el Motor

```python
from criba.catalog import (
    methods,                    # Todos los métodos (4002)
    frameworks,                 # Solo frameworks (111)
    facilitation_patterns,      # Solo patrones de facilitación (25)
    group_games,                # Solo juegos de grupo (19)
    methods_by_source,          # Filtrar por fuente
    methods_by_granularity,     # Filtrar por granularidad
)

# Selección con granularidad
from criba.methods import select_methods
selected = select_methods(
    count=8,
    mode="balanced",
    query="cómo proteger APIs",
    granularity_filter=["micro_technique", "framework"]
)
```

## Equivalencias Detectadas

121 ítems tienen relaciones de equivalencia mapeadas:
- TRIZ clásico ↔ técnicas de ruptura de marco
- SCAMPER ↔ métodos de inversión y sustracción
- Anti-Problem (Gamestorming) ↔ "Invertir el objetivo"
- 1-2-4-All (LS) ↔ métodos de divergencia
- FMEA ↔ técnicas de diseño adversarial

## Estructura de Archivos

```
data/
  methods/
    library_combined.json          # Librería unificada (4002 ítems)
    sources/                       # Fuentes individuales (para referencia)
      source_innovation_frameworks.json
      source_ideo_method_cards.json
      source_liberating_structures.json
      source_brainstorming_techniques.json
      source_gamestorming.json
      source_security_frameworks.json
      source_pentest_methodologies.json
      source_red_team_playbooks.json
      source_incident_response.json
      source_decision_frameworks.json
      source_research_taxonomies.json
    archive/                       # Archivos originales preservados
  schemas/
    ontology.json                  # Ontología de categorías y granularidades
```

## Scripts

| Script | Descripción |
|--------|-------------|
| `scripts/parse_ee_catalogs_v2.py` | Parsea archivos de texto de ee/ a JSON |
| `scripts/merge_libraries_v3.py` | Merge inteligente con schema enriquecido |
| `scripts/regenerate_golden.py` | Regenera golden master tras cambios |
| `scripts/count_catalogs.py` | Cuenta ítems por fuente |
| `scripts/verify_library.py` | Verifica integridad de la librería |

## Verificación

```bash
# Tests completos
python -m pytest tests/ -v

# Conteo total
python -c "from src.criba.catalog import methods; print(len(methods()))"
# → 4002

# Solo frameworks
python -c "from src.criba.catalog import frameworks; print(len(frameworks()))"
# → 111

# Solo patrones de facilitación
python -c "from src.criba.catalog import facilitation_patterns; print(len(facilitation_patterns()))"
# → 25

# Solo juegos de grupo
python -c "from src.criba.catalog import group_games; print(len(group_games()))"
# → 19

# Golden master
python scripts/regenerate_golden.py
```

## Seguridad y Ética

Todos los métodos de seguridad están diseñados para:
- Pentesting autorizado y defensivo
- Análisis de vulnerabilidades en entornos controlados
- Mejora de postura de seguridad
- NO para ataques no autorizados

Los Safety Gates de BLACKFORGE (S0-S3) siguen operando sobre el pipeline.
