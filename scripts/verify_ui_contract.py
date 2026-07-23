#!/usr/bin/env python3
"""
GATE reproducible: verifica que los entregables de la fase de CONTRATO VISUAL
de CRIBA (01_TAREA_ACTUAL.txt, seccion 12) cumplen la especificacion.

No implementa la GUI. Valida que los contratos existen, no estan vacios y
cubren los requisitos normativos de la tarea:
  - S4: tokens de diseno (color/bg/panel/card..., radio, spacing, shadow,
        typography, icon).
  - S5: 7 botones obligatorios documentados.
  - S7: bloques funcionales 7.1..7.7.
  - S10: mapeo PySide6 (widgets obligatorios; QTableWidget O QTableView).
  - S11: 10 estados visuales cubiertos.

Normaliza acentos para comparar sin falsos positivos. Cross-check de
coherencia entre docs y theme_criba.json (fuente unica).

Salida: rc=0 si todo pasa; rc!=0 si hay fallos.
"""
import json
import os
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
DATA = os.path.join(ROOT, "data")

REQUIRED_FILES = [
    os.path.join(DOCS, "UI_CONTRACT_CRIBA.md"),
    os.path.join(DOCS, "STYLE_GUIDE_CRIBA.md"),
    os.path.join(DOCS, "WIDGET_TREE_CRIBA.md"),
    os.path.join(DOCS, "STATE_MATRIX_CRIBA.md"),
    os.path.join(DATA, "theme_criba.json"),
]

# Tokens minimos exigidos por 01_TAREA seccion 4. Se admiten ambas notaciones
# (punto o guion bajo) porque el JSON usa guion bajo y los docs punto.
REQUIRED_THEME_TOKENS = [
    "color.bg.app", "color.bg.panel", "color.bg.card", "color.bg.card.hover",
    "color.border.soft", "color.border.active",
    "color.text.primary", "color.text.secondary", "color.text.muted",
    "color.accent.blue", "color.accent.cyan", "color.accent.violet",
    "color.success", "color.warning", "color.error",
    "color.chart.1", "color.chart.2", "color.chart.3", "color.chart.4", "color.chart.5",
    "radius.sm", "radius.md", "radius.lg", "radius.xl",
    "spacing.4", "spacing.8", "spacing.12", "spacing.16", "spacing.20", "spacing.24", "spacing.32",
    "shadow.sm", "shadow.md", "shadow.glow",
    "typography.display", "typography.h1", "typography.h2", "typography.h3",
    "typography.body", "typography.caption",
    "icon.size.sm", "icon.size.md", "icon.size.lg",
]

REQUIRED_BUTTONS = [
    "Nueva idea", "Generar", "Evaluar", "Guardar",
    "Actualizar innovaciones", "Historial", "Blackforge",
]

REQUIRED_BLOCKS = [
    "MOTOR DE INNOVACION", "IDEA ACTIVA", "RANKING DE IDEAS",
    "FUENTES DE INNOVACION", "CATEGORIAS DE INNOVACION",
    "ACTIVIDAD RECIENTE", "BLACKFORGE",
]

# Seccion 10: lista explicita; QTableWidget se satisface con QTableView.
REQUIRED_WIDGETS = [
    "QMainWindow", "QHBoxLayout", "QVBoxLayout", "QFrame", "QScrollArea",
    "QPushButton", "QTableView", "QTabBar", "QStackedWidget", "QProgressBar",
    "footerStrip",
]
TABLE_WIDGET_ALIASES = ["QTableWidget", "QTableView"]

REQUIRED_STATES = [
    "SIN SESION", "NUEVA IDEA SIN EVALUAR", "GENERANDO", "EVALUANDO",
    "RANKING LISTO", "GUARDADO COMPLETADO", "HISTORIAL CARGADO",
    "SIN FUENTES ACTUALIZADAS", "ERROR DE OPERACION",
    "MODO BLACKFORGE NO ACTIVO",
]

CROSSCHECK = {
    "color.bg.app": "#070D1A",
    "color.bg.panel": "#0B1424",
    "color.accent.cyan": "#22D3EE",
    "color.accent.violet": "#8B5CF6",
    "color.chart.1": "#22D3EE",
    "color.chart.2": "#8B5CF6",
    "color.success": "#10B981",
    "color.error": "#EF4444",
}


def fold(s):
    """Quita acentos y pasa a mayusculas para comparar de forma robusta."""
    n = unicodedata.normalize("NFKD", s)
    n = "".join(c for c in n if not unicodedata.combining(c))
    return n.upper()


def dot_get(d, path):
    cur = d
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def theme_has_token(theme, token):
    """Acepta notacion punto o guion bajo; shadow.glow cubre glow_1/glow_2."""
    alt = token.replace(".", "_")
    for key in (token, alt):
        if dot_get(theme, key) is not None:
            return True
    if token == "shadow.glow":
        return dot_get(theme, "shadow.glow_1") is not None and dot_get(theme, "shadow.glow_2") is not None
    if token == "color.bg.card.hover":
        return dot_get(theme, "color.bg.card_hover") is not None
    return False


def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def main():
    errors = []
    checks = []

    for fp in REQUIRED_FILES:
        if not os.path.isfile(fp):
            errors.append(f"FALTA ARCHIVO: {fp}")
        elif os.path.getsize(fp) == 0:
            errors.append(f"ARCHIVO VACIO: {fp}")
        else:
            checks.append(f"existe+no_vacio: {os.path.basename(fp)}")

    theme_path = os.path.join(DATA, "theme_criba.json")
    theme = None
    if os.path.isfile(theme_path):
        try:
            theme = json.load(open(theme_path, "r", encoding="utf-8"))
        except Exception as e:  # noqa
            errors.append(f"theme_criba.json NO es JSON valido: {e}")
    if theme is not None:
        missing = [t for t in REQUIRED_THEME_TOKENS if not theme_has_token(theme, t)]
        if missing:
            errors.append(f"theme_criba.json falta tokens: {missing}")
        else:
            checks.append(f"tokens_theme: {len(REQUIRED_THEME_TOKENS)} presentes")

        sg = read_text(os.path.join(DOCS, "STYLE_GUIDE_CRIBA.md"))
        bad = []
        for tok, val in CROSSCHECK.items():
            actual = dot_get(theme, tok) or dot_get(theme, tok.replace(".", "_"))
            if actual != val:
                bad.append(f"{tok}: theme={actual} != {val}")
            elif fold(val) not in fold(sg):
                bad.append(f"token {tok}={val} no citado en STYLE_GUIDE")
        if bad:
            errors.extend(bad)
        else:
            checks.append("crosscheck_theme_docs: coherente")

    uc = read_text(os.path.join(DOCS, "UI_CONTRACT_CRIBA.md"))
    uc_f = fold(uc)
    for b in REQUIRED_BUTTONS:
        if fold(b) not in uc_f:
            errors.append(f"UI_CONTRACT falta boton: {b}")
    btn_ok = sum(1 for b in REQUIRED_BUTTONS if fold(b) in uc_f)
    checks.append(f"ui_contract_botones: {btn_ok}/{len(REQUIRED_BUTTONS)}")

    for blk in REQUIRED_BLOCKS:
        if fold(blk) not in uc_f:
            errors.append(f"UI_CONTRACT falta bloque: {blk}")
    blk_ok = sum(1 for blk in REQUIRED_BLOCKS if fold(blk) in uc_f)
    checks.append(f"ui_contract_bloques: {blk_ok}/{len(REQUIRED_BLOCKS)}")

    wt = read_text(os.path.join(DOCS, "WIDGET_TREE_CRIBA.md"))
    all_docs = uc + wt + read_text(os.path.join(DOCS, "STATE_MATRIX_CRIBA.md"))
    for w in REQUIRED_WIDGETS:
        present = w in all_docs
        if w == "QTableView":
            present = any(a in all_docs for a in TABLE_WIDGET_ALIASES)
        if not present:
            errors.append(f"falta widget PySide6: {w}")
    w_ok = 0
    for w in REQUIRED_WIDGETS:
        present = w in all_docs or (w == "QTableView" and any(a in all_docs for a in TABLE_WIDGET_ALIASES))
        w_ok += 1 if present else 0
    checks.append(f"widget_tree: {w_ok}/{len(REQUIRED_WIDGETS)} widgets mapeados")

    sm = read_text(os.path.join(DOCS, "STATE_MATRIX_CRIBA.md"))
    sm_f = fold(sm)
    for s in REQUIRED_STATES:
        if fold(s) not in sm_f:
            errors.append(f"STATE_MATRIX falta estado: {s}")
    st_ok = sum(1 for s in REQUIRED_STATES if fold(s) in sm_f)
    checks.append(f"state_matrix: {st_ok}/{len(REQUIRED_STATES)} estados")

    print("=" * 60)
    print("GATE: CONTRATO VISUAL CRIBA (fase no-implementacion GUI)")
    print("=" * 60)
    for c in checks:
        print(f"  [OK]  {c}")
    for e in errors:
        print(f"  [FAIL] {e}")
    print("=" * 60)
    if errors:
        print(f"RESULTADO: FAIL ({len(errors)} fallos)")
        return 1
    print(f"RESULTADO: PASS ({len(checks)} checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
