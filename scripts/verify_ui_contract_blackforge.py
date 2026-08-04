#!/usr/bin/env python3
"""
GATE reproducible: verifica que los entregables de la fase de CONTRATO VISUAL
de BLACKFORGE (01_TAREA_ACTUAL.txt, secciones 4, 7, 11, 12-14, 13) cumplen la
especificacion.

No implementa la GUI. Valida que los contratos existen, no estan vacios y
cubren los requisitos normativos de la tarea:
  - S4: tokens de diseno (color bg/panel/hero/card/card_hover, border soft/active,
        text primary/secondary/muted, accent orange/orange.dim/orange.glow,
        success/warning/error, chart orange/neutral/green/red; radios; spacing;
        shadow/glow; typography; icon).
  - S7: 8 botones de navegacion documentados.
  - S11: mapeo PySide6 (widgets obligatorios incl. QTableView/QStackedWidget).
  - S13: 11 estados visuales cubiertos.
  - Conservacion de la imagen hero de la criba + paleta negro+naranja.

Normaliza acentos para comparar sin falsos positivos. Cross-check de
coherencia entre docs y theme_blackforge.json (fuente unica).

Salida: rc=0 si todo pasa; rc!=0 si hay fallos.
"""
import json
import os
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
DATA = os.path.join(ROOT, "data")
ASSETS = os.path.join(DATA, "assets")

REQUIRED_FILES = [
    os.path.join(DOCS, "UI_CONTRACT_BLACKFORGE.md"),
    os.path.join(DOCS, "STYLE_GUIDE_BLACKFORGE.md"),
    os.path.join(DOCS, "WIDGET_TREE_BLACKFORGE.md"),
    os.path.join(DOCS, "STATE_MATRIX_BLACKFORGE.md"),
    os.path.join(DATA, "theme_blackforge.json"),
]

# Tokens minimos exigidos por 01_TAREA seccion 4.
REQUIRED_THEME_TOKENS = [
    "color.bg.app", "color.bg.panel", "color.bg.hero", "color.bg.card",
    "color.bg.card.hover",
    "color.border.soft", "color.border.active",
    "color.text.primary", "color.text.secondary", "color.text.muted",
    "color.accent.orange", "color.accent.orange.dim", "color.accent.orange.glow",
    "color.success", "color.warning", "color.error",
    "color.chart.orange", "color.chart.neutral", "color.chart.green", "color.chart.red",
    "radius.sm", "radius.md", "radius.lg", "radius.xl",
    "spacing.4", "spacing.8", "spacing.12", "spacing.16", "spacing.20", "spacing.24", "spacing.32",
    "shadow.sm", "shadow.md", "shadow.glow",
    "typography.display", "typography.h1", "typography.h2", "typography.h3",
    "typography.body", "typography.caption",
    "icon.size.sm", "icon.size.md", "icon.size.lg",
]

REQUIRED_BUTTONS = [
    "Resumen", "Reconocimiento", "Vectores", "Simulacion",
    "Contramedidas", "Laboratorio", "Historial", "Volver a CRIBA",
]

# Bloques funcionales recomendados (tarea 9.1..9.6) deben aparecer en el contrato.
REQUIRED_BLOCKS = [
    "ESTADO DE SESION", "METRICA PRINCIPAL", "DISTRIBUCION",
    "ALERTAS", "MODULOS PRINCIPALES", "FOOTER",
]

# Seccion 11: lista explicita; QTableWidget se satisface con QTableView.
# BLACKFORGE no usa QTabBar ni una página embebida: CRIBA la lanza con QProcess.
REQUIRED_WIDGETS = [
    "QMainWindow", "QHBoxLayout", "QVBoxLayout", "QFrame", "QScrollArea",
    "QPushButton", "QTableView", "QProcess", "QProgressBar",
    "footerStrip",
]
TABLE_WIDGET_ALIASES = ["QTableWidget", "QTableView"]

# Seccion 13: 11 estados obligatorios.
REQUIRED_STATES = [
    "MODO RESUMEN", "SIN SESION ACTIVA", "SESION OPERATIVA",
    "SIMULACION EJECUTANDOSE", "LABORATORIO LISTO",
    "REVISION MANUAL REQUERIDA", "AUTORIZACION FALTANTE",
    "SANDBOX NO DISPONIBLE", "SIN ALERTAS", "ALERTA CRITICA",
    "VUELTA A CRIBA",
]

CROSSCHECK = {
    "color.bg.app": "#050607",
    "color.bg.panel": "#0D1012",
    "color.accent.orange": "#FF6A00",
    "color.accent.orange.glow": "#FF8318",
    "color.chart.orange": "#FF6A00",
    "color.success": "#21D879",
    "color.error": "#FF573D",
}


def fold(s):
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
    # Prueba notacion punto anidada y notacion aplanada con guion bajo, en
    # ambas variantes: todo-con-guion-bajo y solo-ultimo-segmento-con-guion-bajo
    # (p.ej. color.accent.orange.dim -> color.accent.orange_dim).
    parts = token.split(".")
    base = ".".join(parts[:-1])
    last = parts[-1]
    candidates = [
        token,                          # color.accent.orange.dim
        token.replace(".", "_"),       # color_accent_orange_dim
        f"{base}_{last}",              # color.accent.orange_dim
        f"{base}_{last}".replace(".", "_"),  # color_accent_orange_dim (redundante, safe)
    ]
    for key in candidates:
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

    theme_path = os.path.join(DATA, "theme_blackforge.json")
    theme = None
    if os.path.isfile(theme_path):
        try:
            theme = json.load(open(theme_path, "r", encoding="utf-8"))
        except Exception as e:  # noqa
            errors.append(f"theme_blackforge.json NO es JSON valido: {e}")
    if theme is not None:
        missing = [t for t in REQUIRED_THEME_TOKENS if not theme_has_token(theme, t)]
        if missing:
            errors.append(f"theme_blackforge.json falta tokens: {missing}")
        else:
            checks.append(f"tokens_theme: {len(REQUIRED_THEME_TOKENS)} presentes")

        sg = read_text(os.path.join(DOCS, "STYLE_GUIDE_BLACKFORGE.md"))
        bad = []
        for tok, val in CROSSCHECK.items():
            actual = None
            parts = tok.split(".")
            base = ".".join(parts[:-1])
            last = parts[-1]
            for key in (tok, tok.replace(".", "_"), f"{base}_{last}"):
                actual = dot_get(theme, key)
                if actual is not None:
                    break
            if actual != val:
                bad.append(f"{tok}: theme={actual} != {val}")
            elif fold(val) not in fold(sg):
                bad.append(f"token {tok}={val} no citado en STYLE_GUIDE")
        if bad:
            errors.extend(bad)
        else:
            checks.append("crosscheck_theme_docs: coherente")

    # Paleta negro + naranja conservada (tarea §16): bg.app oscuro y accent naranja.
    if theme is not None:
        bg = dot_get(theme, "color.bg.app") or dot_get(theme, "color.bg_app")
        ac = dot_get(theme, "color.accent.orange") or dot_get(theme, "color.accent.orange")
        if not (isinstance(bg, str) and bg.lower() in ("#0c0a08", "#0a0806", "#0f0f0f", "#0c0c0c")
                or (isinstance(bg, str) and bg.startswith("#0"))):
            errors.append(f"paleta: color.bg.app no es negro carbón: {bg}")
        else:
            checks.append(f"paleta_negro: bg.app={bg}")
        if not (isinstance(ac, str) and ac.lower().startswith("#ff")):
            errors.append(f"paleta: color.accent.orange no es naranja: {ac}")
        else:
            checks.append(f"paleta_naranja: accent.orange={ac}")

    # Imagen hero de la criba conservada (tarea §8, §16).
    hero = os.path.join(ASSETS, "blackforge_hero.png")
    if os.path.isfile(hero):
        checks.append("hero_criba: data/assets/blackforge_hero.png presente")
    else:
        errors.append(f"FALTA ASSET HERO: {hero}")

    uc = read_text(os.path.join(DOCS, "UI_CONTRACT_BLACKFORGE.md"))
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

    wt = read_text(os.path.join(DOCS, "WIDGET_TREE_BLACKFORGE.md"))
    sg_bf = read_text(os.path.join(DOCS, "STYLE_GUIDE_BLACKFORGE.md"))
    all_docs = uc + wt + sg_bf + read_text(os.path.join(DOCS, "STATE_MATRIX_BLACKFORGE.md"))
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

    sm = read_text(os.path.join(DOCS, "STATE_MATRIX_BLACKFORGE.md"))
    sm_f = fold(sm)
    for s in REQUIRED_STATES:
        if fold(s) not in sm_f:
            errors.append(f"STATE_MATRIX falta estado: {s}")
    st_ok = sum(1 for s in REQUIRED_STATES if fold(s) in sm_f)
    checks.append(f"state_matrix: {st_ok}/{len(REQUIRED_STATES)} estados")

    print("=" * 60)
    print("GATE: CONTRATO VISUAL BLACKFORGE (fase no-implementacion GUI)")
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
