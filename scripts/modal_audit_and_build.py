"""
Modal script: auditoría masiva + análisis catalogo + preparación build CRIBA/BLACKFORGE.

Ejecutar:
  modal run scripts/modal_audit_and_build.py

Fases:
  A) Inventario catálogos EE (parseo, conteos, duplicados, ejes morfológicos)
  B) Análisis catálogo actual vs fuentes
  C) Tests completos
  D) Análisis código UI blackforge_screen.py
  E) Resumen compacto para Sonnet
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys
from pathlib import Path
from typing import Any

import modal

REPO_ROOT = pathlib.Path("E:/PROYECTS/CRIBA")
EE_ROOT = pathlib.Path("C:/Users/KLSX/Downloads/ee")
REMOTE_ROOT = "/criba"
REMOTE_EE = "/ee"

_PINNED = (
    "pytest==9.1.1",
    "pytest-timeout==2.4.0",
    "pydantic>=2.0",
    "hypothesis==6.161.1",
    "charset-normalizer",
)

# Construir imagen con el repo y los catálogos EE
image = modal.Image.debian_slim(python_version="3.12").pip_install(*_PINNED)

for _item in ["src", "data", "tests", "imports", "pyproject.toml"]:
    _local = REPO_ROOT / _item
    if _local.exists():
        _remote = f"{REMOTE_ROOT}/{_item}"
        image = (
            image.add_local_dir(str(_local), _remote)
            if _local.is_dir()
            else image.add_local_file(str(_local), _remote)
        )

# Montar los catálogos EE
if EE_ROOT.exists():
    image = image.add_local_dir(str(EE_ROOT), REMOTE_EE)

app = modal.App("criba-blackforge-audit-v2", image=image)


# ---------------------------------------------------------------------------
# Helpers de parseo (se ejecutan en cloud)
# ---------------------------------------------------------------------------

def _parse_numbered(raw: str, axis: str, source_key: str) -> list[dict]:
    pattern = re.compile(r'^(\d+)\.\s+(.+?)(?=^\d+\.\s|\Z)', re.MULTILINE | re.DOTALL)
    entries = []
    for m in pattern.finditer(raw):
        num = int(m.group(1))
        text = re.sub(r'\s+', ' ', m.group(2).strip().replace('\n', ' '))
        if ' — ' in text:
            name, desc = text.split(' — ', 1)
        elif ': ' in text[:100]:
            name, desc = text.split(': ', 1)
        else:
            name, desc = text[:80], text
        norm = re.sub(r'[^a-z0-9]', '', name.lower()[:80])
        entries.append({
            "id": f"{source_key}_{num:04d}",
            "num": num,
            "name": name.strip()[:120],
            "template": desc.strip()[:500],
            "axis": axis,
            "source": source_key,
            "normalized_mechanism": norm,
        })
    return entries


def _parse_metodologias(raw: str) -> list[dict]:
    entries = []
    for line in raw.splitlines():
        if '>' not in line:
            continue
        parts = [p.strip() for p in line.split('>')]
        if len(parts) < 4:
            continue
        tipo_sector, num_str, name = parts[0], parts[1], parts[2]
        desc = '>'.join(parts[3:])
        try:
            num = int(num_str)
        except ValueError:
            continue
        sector = "general"
        if ',' in tipo_sector:
            _, sector = tipo_sector.split(',', 1)
            sector = sector.strip().lower().replace(' ', '_')
        norm = re.sub(r'[^a-z0-9]', '', name.lower()[:80])
        entries.append({
            "id": f"metodologias_{num:04d}",
            "num": num,
            "name": name.strip()[:120],
            "template": desc.strip()[:500],
            "axis": "methodology",
            "sector": sector,
            "source": "metodologias_2000",
            "normalized_mechanism": norm,
        })
    return entries


def _parse_tecnicas_max(raw: str) -> list[dict]:
    entries = []
    blocks = re.split(r'\n(?=\d+\.\s)', raw)
    for block in blocks:
        m_num = re.match(r'^(\d+)\.\s+', block)
        if not m_num:
            continue
        num = int(m_num.group(1))
        campo = re.search(r'CAMPO[:\s]+(.+)', block)
        nombre = re.search(r'NOMBRE[:\s]+(.+)', block)
        desc = re.search(r'DESCRIPCI[OÓ]N[:\s]+(.+)', block, re.DOTALL)
        name = nombre.group(1).strip()[:120] if nombre else f"Tecnica_{num}"
        template = desc.group(1).strip()[:500] if desc else ""
        norm = re.sub(r'[^a-z0-9]', '', name.lower()[:80])
        entries.append({
            "id": f"tecnicas_max_{num:04d}",
            "num": num,
            "name": name,
            "template": template,
            "axis": "methodology",
            "sector": campo.group(1).strip() if campo else "general",
            "source": "tecnicas_max",
            "normalized_mechanism": norm,
        })
    return entries


def _extract_morphological_axes() -> list[dict]:
    """Ejes morfológicos adicionales del debate (Actor, Entrada, Restricción…)"""
    axes_data: dict[str, list[str]] = {
        "actor": [
            "usuario", "desarrollador", "agente IA", "sistema/dato",
            "auditor", "adversario", "tercero afectado", "actor no humano",
            "agente local", "multi-agente", "humano+IA", "hardware",
        ],
        "entrada": [
            "prompt", "código", "logs", "evidencia", "evento",
            "contradicción", "fallo real", "señal externa",
            "voz", "sensores", "Kanban", "clima",
        ],
        "restriccion": [
            "coste cero", "offline", "hardware limitado", "tiempo extremo",
            "datos mínimos", "confianza cero", "solo reversible",
            "sin autoridad central", "8 GB RAM", "sin GPU", "solo terminal",
        ],
        "salida": [
            "idea", "arquitectura", "mecanismo", "test", "experimento",
            "política/gate", "contraejemplo", "prototipo",
            "código", "automatización", "invento físico", "prompt reutilizable",
        ],
        "dominio_externo": [
            "biología", "física", "ecología", "industria", "derecho",
            "economía", "música/arte", "ajedrez/juegos",
            "ciclismo", "electrónica DIY", "TRIZ", "biomimética",
        ],
        "escala": [
            "componente", "aplicación", "proyecto", "equipo",
            "organización", "ecosistema",
        ],
        "tiempo": [
            "instantáneo", "una sesión", "una iteración",
            "ciclo de vida", "años", "generaciones",
        ],
        "grado_ruptura": [
            "conservador", "moderado", "fuerte", "absurdo-productivo",
        ],
        "orientacion": [
            "prevención", "detección", "resistencia", "recuperación", "evolución",
        ],
    }
    entries = []
    idx = 1
    for ax_name, values in axes_data.items():
        for val in values:
            norm = re.sub(r'[^a-z0-9]', '', val.lower()[:80])
            entries.append({
                "id": f"morpho_{ax_name}_{idx:04d}",
                "num": idx,
                "name": val,
                "template": f"Propiedad morfológica {ax_name}: {val}",
                "axis": "morphological",
                "morpho_axis": ax_name,
                "source": "debate_morfologico",
                "normalized_mechanism": norm,
            })
            idx += 1
    return entries


# ---------------------------------------------------------------------------
# Función principal Modal
# ---------------------------------------------------------------------------

@app.function(timeout=600, cpu=4)
def full_audit() -> dict[str, Any]:
    import subprocess
    import json
    import re
    import sys
    from pathlib import Path

    sys.path.insert(0, "/criba/src")
    ee = Path("/ee")
    criba = Path("/criba")
    results: dict[str, Any] = {}

    # =========================================================
    # FASE A: Inventario y parseo de TODOS los catálogos EE
    # =========================================================
    print("=== FASE A: Inventario catálogos EE ===")

    catalog_files = {
        "lentes_1700":       (ee / "TODAS_LAS_LENTES_1-1700.txt",                          "perspective", "lentes_1700"),
        "ruptura_1100":      (ee / "1100_tecnicas_ruptura_de_marco_AMPLIADO_VALIDADO.txt",  "ruptura",     "ruptura_1100"),
        "escape_1100":       (ee / "1100_tecnicas_salto_espacio_conocido_AMPLIADO_VALIDADO.txt", "escape", "escape_1100"),
        "escape_1030_master":(ee / "1030_tecnicas_salto_fuera_espacio_conocido_MASTER.txt", "escape",      "escape_1030"),
        "generation_900":    (ee / "900_metodos_ideas_disruptivas_AMPLIADO_VALIDADO.txt",   "generation",  "gen_900"),
        "ruptura_1000_old":  (ee / "1000_tecnicas_ruptura_de_marco.txt",                    "ruptura",     "ruptura_1000_old"),
    }

    parsed: dict[str, list] = {}
    inventory: dict[str, dict] = {}

    for key, (path, axis, src_key) in catalog_files.items():
        if not path.exists():
            inventory[key] = {"status": "MISSING", "path": str(path)}
            print(f"  {key}: MISSING")
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        entries = _parse_numbered(raw, axis, src_key)
        parsed[key] = entries
        norms = [e["normalized_mechanism"] for e in entries]
        inventory[key] = {
            "status": "OK",
            "file_size": path.stat().st_size,
            "entry_count": len(entries),
            "unique_norms": len(set(norms)),
            "max_num": max((e["num"] for e in entries), default=0),
        }
        print(f"  {key}: {len(entries)} entries")

    # Metodologías 2000
    meto_entries: list[dict] = []
    for part in ["catalogo_tecnicas_metodologias_parte_1.txt",
                 "catalogo_tecnicas_metodologias_parte_2.txt",
                 "catalogo_tecnicas_metodologias_parte_3.txt"]:
        p = ee / "tecnicasmetodologias2000" / part
        if p.exists():
            meto_entries.extend(_parse_metodologias(p.read_text(encoding="utf-8", errors="replace")))

    # Técnicas max
    tecmax_path = ee / "tecnicas_metodologias_max.txt"
    tecmax_entries = _parse_tecnicas_max(tecmax_path.read_text(encoding="utf-8", errors="replace")) if tecmax_path.exists() else []

    parsed["metodologias_2000"] = meto_entries
    parsed["tecnicas_max"] = tecmax_entries
    inventory["metodologias_2000"] = {"entry_count": len(meto_entries)}
    inventory["tecnicas_max"] = {"entry_count": len(tecmax_entries)}
    print(f"  metodologias_2000: {len(meto_entries)} entries")
    print(f"  tecnicas_max: {len(tecmax_entries)} entries")
    results["inventory"] = inventory

    # =========================================================
    # FASE B: Diff MASTER 1030 vs AMPLIADO 1100 (escape)
    # =========================================================
    print("=== FASE B: Diff MASTER vs AMPLIADO escape ===")

    if "escape_1030_master" in parsed and "escape_1100" in parsed:
        norms_1030 = {e["normalized_mechanism"]: e for e in parsed["escape_1030_master"]}
        norms_1100 = {e["normalized_mechanism"]: e for e in parsed["escape_1100"]}
        only_1030 = {k: v for k, v in norms_1030.items() if k not in norms_1100}
        only_1100 = {k: v for k, v in norms_1100.items() if k not in norms_1030}
        shared = len([k for k in norms_1030 if k in norms_1100])
        results["escape_diff"] = {
            "escape_1030_total": len(parsed["escape_1030_master"]),
            "escape_1100_total": len(parsed["escape_1100"]),
            "shared": shared,
            "only_in_1030": len(only_1030),
            "only_in_1100": len(only_1100),
            "sample_only_1030": [v["name"] for v in list(only_1030.values())[:10]],
            "sample_only_1100": [v["name"] for v in list(only_1100.values())[:10]],
        }
        print(f"  shared={shared}, only_1030={len(only_1030)}, only_1100={len(only_1100)}")

    # =========================================================
    # FASE C: Ejes morfológicos
    # =========================================================
    print("=== FASE C: Ejes morfológicos adicionales ===")
    morpho_entries = _extract_morphological_axes()
    results["morphological_axes"] = {
        "total_entries": len(morpho_entries),
        "axes": list({e["morpho_axis"] for e in morpho_entries}),
        "per_axis": {ax: len([e for e in morpho_entries if e.get("morpho_axis") == ax])
                     for ax in {e.get("morpho_axis", "?") for e in morpho_entries}},
        "sample": morpho_entries[:5],
    }
    print(f"  Morpho: {len(morpho_entries)} entries, axes: {results['morphological_axes']['axes']}")

    # =========================================================
    # FASE D: Catálogo actual vs fuentes
    # =========================================================
    print("=== FASE D: Catálogo actual ===")
    lib_path = criba / "data" / "methods" / "library_combined.json"
    catalog_stats: dict[str, Any] = {}
    if lib_path.exists():
        lib = json.loads(lib_path.read_text(encoding="utf-8"))
        by_axis: dict[str, int] = {}
        for e in lib:
            ax = e.get("axis", "?")
            by_axis[ax] = by_axis.get(ax, 0) + 1
        total_ee = sum(
            inventory.get(k, {}).get("entry_count", 0)
            for k in ["lentes_1700", "ruptura_1100", "escape_1100",
                       "generation_900", "metodologias_2000", "tecnicas_max"]
        )
        catalog_stats = {
            "library_combined_total": len(lib),
            "by_axis": by_axis,
            "ee_sources_total": total_ee,
            "escape_unique_in_master": results.get("escape_diff", {}).get("only_in_1030", 0),
            "morphological_new": len(morpho_entries),
            "potential_total_after_expansion": len(lib) + len(morpho_entries) + results.get("escape_diff", {}).get("only_in_1030", 0),
        }
        print(f"  Library: {len(lib)}, EE sources: {total_ee}, morpho_new: {len(morpho_entries)}")
    results["catalog_analysis"] = catalog_stats

    # =========================================================
    # FASE E: Tests completos (con hypothesis instalado ahora)
    # =========================================================
    print("=== FASE E: Tests ===")
    r = subprocess.run(
        ["python", "-m", "pytest", "/criba/tests",
         "-q", "--tb=short", "--timeout=60", "-x"],
        capture_output=True, text=True, cwd="/criba",
        env={**os.environ, "PYTHONPATH": "/criba/src", "QT_QPA_PLATFORM": "offscreen"}
    )
    lines_out = (r.stdout + r.stderr).splitlines()
    summary = [l for l in lines_out if "passed" in l or "failed" in l or "error" in l.lower()]
    results["tests"] = {
        "exit_code": r.returncode,
        "summary": summary[-5:] if summary else [],
        "last_lines": lines_out[-10:],
    }
    print(f"  Tests rc={r.returncode}: {summary[-1] if summary else 'no output'}")

    # =========================================================
    # FASE F: Análisis código UI
    # =========================================================
    print("=== FASE F: UI Analysis ===")

    def _analyze_ui_file(path: Path, label: str) -> dict:
        if not path.exists():
            return {"status": "MISSING"}
        code = path.read_text(encoding="utf-8")
        return {
            "lines": len(code.splitlines()),
            "classes": re.findall(r'class\s+(\w+)\s*\(', code),
            "public_methods": len(re.findall(r'\n    def [^_]', code)),
            "has_3_modes": {
                "optimizado": "optimizado" in code.lower() or "modo_opt" in code.lower(),
                "loteria_asociativa": "asociativa" in code.lower() and "loteria" in code.lower(),
                "loteria_pura": "pura" in code.lower() and "loteria" in code.lower(),
            },
            "uses_real_engine": "from ..engine" in code or "activate(" in code,
            "uses_bf_catalog": "bf_records" in code or "blackforge_catalog" in code,
            "has_execute_btn": "EJECUTAR" in code or "ejecutar" in code.lower(),
            "has_live_clock": "QTimer" in code and ("setText" in code or "bfTime" in code),
            "has_sidebar": "navBtn" in code or "NavButton" in code or "sidebar" in code.lower(),
            "has_ideas_table": "QTableView" in code or "QAbstractTableModel" in code,
            "has_donut_chart": "Donut" in code or "DonutChart" in code,
            "has_kpi_panel": "kpi" in code.lower() or "KPI" in code,
            "has_models_section": "Modelo local" in code or "modelo_local" in code.lower(),
            "has_verification_section": "verificaci" in code.lower() or "Juez" in code,
        }

    ui_bf = _analyze_ui_file(
        criba / "src" / "criba" / "ui" / "blackforge_screen.py", "blackforge_screen")
    ui_main = _analyze_ui_file(
        criba / "src" / "criba" / "ui" / "main_window.py", "main_window")
    ui_tokens = _analyze_ui_file(
        criba / "src" / "criba" / "ui" / "tokens.py", "tokens")

    results["ui_analysis"] = {
        "blackforge_screen": ui_bf,
        "main_window": ui_main,
        "tokens": ui_tokens,
    }
    print(f"  BF screen: {ui_bf.get('lines')} lines, modes={ui_bf.get('has_3_modes')}")

    # =========================================================
    # FASE G: Gaps y resumen compacto para Sonnet
    # =========================================================
    print("=== FASE G: Gap analysis ===")
    gaps = []

    if results.get("escape_diff", {}).get("only_in_1030", 0) > 0:
        gaps.append({
            "id": "GAP_001", "severity": "medium", "area": "catalog",
            "description": f"escape_1030 MASTER tiene {results['escape_diff']['only_in_1030']} técnicas únicas no en library_combined (axis=escape)",
            "action": "Integrar técnicas únicas de MASTER al library_combined",
        })

    gaps.append({
        "id": "GAP_002", "severity": "high", "area": "engine",
        "description": f"9 ejes morfológicos del debate ({len(morpho_entries)} valores: actor/entrada/restriccion/salida/dominio/escala/tiempo/grado_ruptura/orientacion) no están en el motor",
        "action": "Añadir ejes morfológicos al motor de activación y al packet de salida",
    })

    modes = ui_bf.get("has_3_modes", {})
    missing_modes = [k for k, v in modes.items() if not v]
    if missing_modes:
        gaps.append({
            "id": "GAP_003", "severity": "high", "area": "ui_blackforge",
            "description": f"Modos no detectados en BF screen: {missing_modes}",
            "action": "Verificar que los 3 modos tienen callbacks reales al motor",
        })

    if not ui_bf.get("has_live_clock"):
        gaps.append({
            "id": "GAP_004", "severity": "low", "area": "ui_blackforge",
            "description": "No se detecta reloj en vivo con QTimer en BF screen",
            "action": "Añadir QTimer que actualice fecha/hora cada segundo en header BF",
        })

    results["gaps"] = gaps
    results["gaps_summary"] = {
        "total": len(gaps),
        "high": sum(1 for g in gaps if g["severity"] == "high"),
        "medium": sum(1 for g in gaps if g["severity"] == "medium"),
        "low": sum(1 for g in gaps if g["severity"] == "low"),
    }

    results["SONNET_SUMMARY"] = {
        "catalog": {
            "current_total": catalog_stats.get("library_combined_total", 0),
            "after_expansion": catalog_stats.get("potential_total_after_expansion", 0),
            "escape_unique_in_master": results.get("escape_diff", {}).get("only_in_1030", 0),
            "morpho_new_values": len(morpho_entries),
            "morpho_axes": results["morphological_axes"]["axes"],
        },
        "tests": {
            "exit_code": results["tests"]["exit_code"],
            "summary": results["tests"]["summary"],
        },
        "ui_blackforge": {
            "lines": ui_bf.get("lines"),
            "has_3_modes": ui_bf.get("has_3_modes"),
            "uses_real_engine": ui_bf.get("uses_real_engine"),
            "has_ideas_table": ui_bf.get("has_ideas_table"),
            "has_live_clock": ui_bf.get("has_live_clock"),
            "has_kpi_panel": ui_bf.get("has_kpi_panel"),
        },
        "gaps": results["gaps_summary"],
        "gaps_detail": gaps,
        "recommendation": (
            "1) Expandir catálogo con ejes morfológicos + escape_master uniques. "
            "2) Completar UI BF con reloj en vivo y 3 modos funcionales verificados. "
            "3) Fijar tests (hypothesis ya disponible en Modal)."
        ),
    }

    print("\n" + "=" * 50)
    print("SONNET_SUMMARY:")
    print(json.dumps(results["SONNET_SUMMARY"], indent=2, ensure_ascii=False))

    return results


@app.local_entrypoint()
def main() -> None:
    import json
    from pathlib import Path

    print("Lanzando auditoría Modal CRIBA/BLACKFORGE...")
    result = full_audit.remote()

    out = Path("E:/PROYECTS/CRIBA/artifacts/modal_audit_result.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Guardado: {out}")

    summary = result.get("SONNET_SUMMARY", {})
    print("\n" + "=" * 60)
    print("RESUMEN COMPACTO PARA SONNET:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
