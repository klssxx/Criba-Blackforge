"""QSS global generado desde data/theme_criba.json.

Contrato STYLE_GUIDE_CRIBA.md §6: prohibido setStyleSheet() por widget en la
implementación; todo estilo via este QSS global + objectName / propiedades
dinámicas. Únicas excepciones permitidas: widgets pintados con QPainter y
delegates (que leen tokens directamente).
"""
from __future__ import annotations

from .tokens import Tokens, load_tokens


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{int(alpha * 255)})"


def build_qss(t: Tokens | None = None) -> str:
    t = t or load_tokens()
    ty = t.type_scale
    display, h1, h2, h3, body, caption = (
        ty("display"), ty("h1"), ty("h2"), ty("h3"), ty("body"), ty("caption"))
    cta_a, cta_b = t.gradient("cta")
    bf_a, bf_b = t.gradient("blackforge")
    return f"""
/* ===== base ===== */
QMainWindow, QWidget#appRoot {{
  background: {t.bg_app};
}}
QWidget {{
  color: {t.text_primary};
  font-family: {t.font_family};
  font-size: {body.size_px}px;
}}
QToolTip {{
  background: {t.bg_inset}; color: {t.text_primary};
  border: 1px solid {t.border_soft}; border-radius: {t.radius('sm')}px;
  padding: {t.spacing(8)}px; font-size: {caption.size_px + 1}px;
}}

/* ===== zonas ===== */
QFrame#sidebar {{
  background: {t.bg_panel};
  border-right: 1px solid {t.border_soft};
}}
QFrame#topbar {{
  background: {t.bg_panel};
  border-bottom: 1px solid {t.border_soft};
}}
QFrame#footerStrip {{
  background: {t.bg_panel};
  border-top: 1px solid {t.border_soft};
}}
QFrame#vline {{
  background: {t.border_soft}; max-width: 1px; min-width: 1px;
  margin-top: 8px; margin-bottom: 8px;
}}

/* ===== marca ===== */
QLabel#brandLogo {{
  font-size: {display.size_px}px; font-weight: {display.weight};
  letter-spacing: 2px;
}}
QLabel#brandTagline {{
  color: {t.text_muted}; font-size: {caption.size_px}px;
  font-weight: {caption.weight}; letter-spacing: 3px;
}}

/* ===== nav (7 botones, UI_CONTRACT §5) — estilo card de la referencia ===== */
QPushButton#navbtn, QPushButton#navbtnBlackforge {{
  background: {t.bg_card}; border: 1px solid {t.border_soft};
  border-radius: {t.radius('md')}px;
  padding: 0px; text-align: left;
  border-left: 3px solid {t.border_soft};
}}
QPushButton#navbtn:hover, QPushButton#navbtnBlackforge:hover {{
  background: {t.bg_card_hover}; border-color: {_rgba(t.accent_cyan, 0.5)};
}}
QPushButton#navbtn:checked {{
  background: {t.bg_card_hover};
  border-left: 3px solid {t.accent_cyan};
  border-color: {_rgba(t.accent_cyan, 0.5)};
}}
QPushButton#navbtn:disabled, QPushButton#navbtnBlackforge:disabled {{
  background: {_rgba(t.bg_card, 0.5)};
}}
QPushButton#navbtn[navstate="running"] {{
  background: {t.bg_card};
  border-left: 3px solid {t.accent_blue};
}}
QPushButton#navbtn[navstate="done"] {{
  border-left: 3px solid {t.success};
}}
QPushButton#navbtn[navstate="error"] {{
  border-left: 3px solid {t.error};
}}
QPushButton#navbtn[suggested="true"] {{
  border: 1px solid {t.border_active};
  border-left: 3px solid {t.accent_cyan};
}}
QPushButton#navbtnBlackforge {{
  background: {t.bg_card};
  border: 1px solid {_rgba(bf_a, 0.40)};
  border-left: 3px solid {_rgba(bf_a, 0.40)};
}}
QLabel#navText {{ font-size: {body.size_px}px; font-weight: 600; background: transparent; }}
QLabel#navSub  {{ color: {t.text_muted}; font-size: {caption.size_px}px; background: transparent; }}
QLabel#navSub[navstate="running"] {{ color: {t.accent_blue}; }}
QLabel#navSub[navstate="error"]   {{ color: {t.error}; }}
QLabel#navIcon {{ font-size: {t.icon_size('md')}px; color: {t.text_secondary}; background: transparent; }}

/* ===== teaser mini sidebar ===== */
QFrame#blackforgeTeaserMini {{
  background: {t.bg_card};
  border: 1px solid {_rgba(bf_a, 0.45)};
  border-radius: {t.radius('md')}px;
}}
QFrame#blackforgeTeaserMini:hover {{ background: {t.bg_card_hover}; }}
QLabel#bfMiniLogo {{
  font-size: {h3.size_px}px; font-weight: 800; letter-spacing: 2px;
  color: {bf_a}; background: transparent;
}}
QLabel#bfMiniTag {{
  color: {t.text_muted}; font-size: {caption.size_px - 1}px;
  letter-spacing: 2px; background: transparent;
}}

/* ===== top bar ===== */
QLabel#greetingTitle {{ font-size: {h2.size_px}px; font-weight: {h2.weight}; }}
QLabel#greetingSub   {{ color: {t.text_secondary}; font-size: {caption.size_px}px; }}
QLabel#dateLabel {{
  color: {t.text_muted}; font-size: {caption.size_px}px;
  font-weight: {caption.weight}; letter-spacing: 1px;
}}
QLabel#timeLabel {{
  font-size: {h3.size_px}px; font-weight: {h3.weight};
  font-family: "Consolas", "Cascadia Mono", monospace;
}}
QToolButton#notifBtn {{
  background: transparent; border: 1px solid {t.border_soft};
  border-radius: {t.radius('md')}px; padding: 6px;
  font-size: {t.icon_size('md') - 4}px; color: {t.text_secondary};
}}
QToolButton#notifBtn:hover {{ border-color: {t.border_active}; color: {t.text_primary}; }}

/* ===== cards ===== */
QFrame#card {{
  background: {t.bg_card};
  border: 1px solid {t.border_soft};
  border-radius: {t.radius('lg')}px;
}}
QFrame#card:hover {{
  border-color: {_rgba(t.border_active, 0.45)};
}}
QFrame#cardAccent {{
  background: {t.bg_card};
  border: 1px solid {t.border_soft};
  border-radius: {t.radius('xl')}px;
  border-top: 2px solid {t.accent_cyan};
}}
QFrame#cardAccent[accent="blackforge"] {{
  border-top: 2px solid {bf_a};
  border-bottom: 1px solid {_rgba(bf_b, 0.35)};
}}
QLabel#sectionTitle {{
  font-size: {h3.size_px}px; font-weight: {h3.weight};
  letter-spacing: 1.5px; background: transparent;
}}
QLabel#sectionDesc {{
  color: {t.text_secondary}; font-size: {caption.size_px}px;
  background: transparent;
}}

/* ===== idea activa ===== */
QLabel#ideaKicker {{
  color: {t.accent_cyan}; font-size: {h3.size_px}px; font-weight: {h3.weight};
  letter-spacing: 1.5px; background: transparent;
}}
QLabel#ideaTitle {{
  font-size: {h1.size_px}px; font-weight: {h1.weight}; background: transparent;
}}
QLabel#ideaSummary {{
  color: {t.text_secondary}; font-size: {body.size_px}px; background: transparent;
}}
QLabel#metricValue {{
  font-size: {h2.size_px}px; font-weight: {h2.weight}; background: transparent;
}}
QLabel#metricLabel {{
  color: {t.text_muted}; font-size: {caption.size_px}px; background: transparent;
}}

/* ===== chips (STYLE_GUIDE §4.6) ===== */
QLabel#chip {{
  border-radius: {t.radius('sm')}px; padding: 2px 8px;
  font-size: {caption.size_px}px; font-weight: 700;
  background: {_rgba(t.text_muted, 0.15)}; color: {t.text_muted};
}}
QLabel#chip[kind="eval"]        {{ background: {_rgba(t.accent_blue, 0.15)};  color: {t.accent_blue}; }}
QLabel#chip[kind="candidata"]   {{ background: {_rgba(t.accent_violet, 0.15)}; color: {t.accent_violet}; }}
QLabel#chip[kind="exploracion"] {{ background: {_rgba(t.text_muted, 0.15)};   color: {t.text_muted}; }}
QLabel#chip[kind="guardada"]    {{ background: {_rgba(t.success, 0.15)};      color: {t.success}; }}
QLabel#chip[kind="error"]       {{ background: {_rgba(t.error, 0.15)};        color: {t.error}; }}

/* ===== ranking ===== */
QTabBar#rankingTabs {{ background: transparent; }}
QTabBar#rankingTabs::tab {{
  background: transparent; color: {t.text_muted};
  padding: 6px 12px; margin-right: {t.spacing(8)}px;
  border: none; border-bottom: 2px solid transparent;
  font-size: {caption.size_px + 1}px; font-weight: 600;
}}
QTabBar#rankingTabs::tab:selected {{
  color: {t.text_primary}; border-bottom: 2px solid {t.accent_cyan};
}}
QTableView#rankingTable {{
  background: transparent; border: none;
  gridline-color: transparent;
  selection-background-color: {t.bg_card_hover};
  selection-color: {t.text_primary};
  alternate-background-color: {_rgba(t.bg_card_hover, 0.45)};
}}
QTableView#rankingTable::item {{ border: none; padding-left: 6px; }}
QHeaderView::section {{
  background: transparent; color: {t.text_muted};
  font-size: {caption.size_px}px; font-weight: 600;
  border: none; border-bottom: 1px solid {t.border_soft};
  padding: 6px; text-transform: uppercase;
}}

/* ===== botones ===== */
QPushButton#primary {{
  background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {cta_a}, stop:1 {cta_b});
  color: {t.text_primary}; border: none; border-radius: {t.radius('md')}px;
  min-height: 38px; padding: 0 {t.spacing(16)}px; font-weight: 600;
}}
QPushButton#primary:hover {{
  background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {_rgba(cta_a, 0.92)}, stop:1 {_rgba(cta_b, 0.92)});
}}
QPushButton#primary:disabled {{ background: #24344F; color: {t.text_muted}; }}
QPushButton#ghost {{
  background: transparent; border: 1px solid {t.border_soft};
  color: {t.text_secondary}; border-radius: {t.radius('md')}px;
  min-height: 34px; padding: 0 {t.spacing(12)}px;
}}
QPushButton#ghost:hover {{ border-color: {t.border_active}; color: {t.text_primary}; }}
QPushButton#ghost:disabled {{ color: {_rgba(t.text_muted, 0.4)}; }}
QPushButton#ghost[freshness="warn"] {{ border-color: {t.warning}; color: {t.warning}; }}
QPushButton#linkBtn {{
  background: transparent; border: none; color: {t.accent_cyan};
  font-size: {caption.size_px + 1}px; text-align: left; padding: 4px 0;
}}
QPushButton#linkBtn:hover {{ text-decoration: underline; }}

/* ===== footer ===== */
QLabel#footerKey {{ color: {t.text_muted}; font-size: {caption.size_px}px; background: transparent; }}
QLabel#footerVal {{
  color: {t.text_primary}; font-size: {caption.size_px}px; font-weight: 600;
  font-family: "Consolas", "Cascadia Mono", monospace; background: transparent;
}}
QLabel#footerVal[freshness="ok"]    {{ color: {t.success}; }}
QLabel#footerVal[freshness="warn"]  {{ color: {t.warning}; }}
QLabel#footerVal[freshness="stale"] {{ color: {t.error}; }}

/* ===== inputs / dialogs ===== */
QTextEdit, QPlainTextEdit, QLineEdit {{
  background: {t.bg_inset}; border: 1px solid {t.border_soft};
  border-radius: {t.radius('md')}px; padding: {t.spacing(8)}px;
  color: {t.text_primary}; selection-background-color: {t.accent_blue};
}}
QTextEdit:focus, QLineEdit:focus {{ border-color: {t.border_active}; }}
QDialog {{ background: {t.bg_panel}; }}
QListWidget {{
  background: {t.bg_inset}; border: 1px solid {t.border_soft};
  border-radius: {t.radius('md')}px;
}}
QListWidget::item {{ padding: 8px; border-radius: {t.radius('sm')}px; }}
QListWidget::item:selected {{ background: {t.bg_card_hover}; }}

/* ===== barras fuentes ===== */
QProgressBar#sourceBar {{
  background: {t.bg_inset}; border: none; border-radius: 3px;
  max-height: 6px; min-height: 6px;
}}
QProgressBar#sourceBar::chunk {{ background: {t.chart(1)}; border-radius: 3px; }}

/* ===== banner error (STATE_MATRIX S9) ===== */
QFrame#errorBanner {{
  background: {_rgba(t.error, 0.12)};
  border: 1px solid {t.error};
  border-radius: {t.radius('md')}px;
}}
QLabel#errorBannerText {{ color: {t.text_primary}; background: transparent; }}

/* ===== BLACKFORGE dashboard industrial (CRIBA BLACKFORCE literal) ===== */
QLabel#bfWordmark {{
  font-size: {display.size_px + 6}px; font-weight: 800; letter-spacing: 1px;
  background: transparent;
}}
QLabel#bfCriba {{ color: {bf_a}; }}
QLabel#bfForce {{ color: {t.text_primary}; }}
QLabel#bfBuilt {{ color: {bf_a}; font-size: {caption.size_px}px; letter-spacing: 3px; background: transparent; }}

QFrame#bfHero {{
  background: qradialgradient(cx:50%, cy:42%, radius:75%,
    stop:0 {t.bg_card_hover}, stop:1 {t.bg_hero});
  border: 1px solid {t.border_soft};
  border-radius: {t.radius('xl')}px;
  overflow: hidden;
}}
QLabel#bfHeroOverlay {{
  background: transparent; font-size: {h2.size_px}px; font-weight: 700;
  letter-spacing: 2px; color: {t.text_primary};
}}
QPushButton#bf3d {{
  background: {_rgba(t.bg_app, 0.6)};
  border: 1px solid {bf_a};
  color: {bf_a}; border-radius: {t.radius('md')}px;
  padding: 8px 16px; font-weight: 600;
}}
QPushButton#bf3d:hover {{ background: {_rgba(bf_a, 0.18)}; color: {bf_b}; }}

QFrame#bfGaugeCard {{
  background: {t.bg_card}; border: 1px solid {t.border_soft};
  border-radius: {t.radius('lg')}px;
  border-top: 2px solid {bf_a};
}}
QLabel#bfGaugeTitle {{ color: {t.text_secondary}; font-size: {caption.size_px}px;
  font-weight: 600; letter-spacing: 1px; background: transparent; }}

QFrame#bfSysCard {{
  background: {t.bg_card}; border: 1px solid {t.border_soft};
  border-radius: {t.radius('md')}px;
  border-left: 2px solid transparent;
}}
QFrame#bfSysCard:hover {{
  background: {t.bg_card_hover};
  border-left: 2px solid {_rgba(bf_a, 0.65)};
}}
QFrame#bfSysCard[accent="blackforge"] {{
  border-left: 3px solid {bf_a};
  background: {_rgba(bf_a, 0.07)};
}}
QLabel#bfSysIcon {{
  color: {bf_a}; font-size: {t.icon_size('lg') - 6}px; background: transparent;
}}
QLabel#bfSysName {{ color: {t.text_muted}; font-size: {caption.size_px}px;
  letter-spacing: 1px; background: transparent; }}
QLabel#bfSysValue {{ color: {t.text_primary}; font-size: {h1.size_px}px;
  font-weight: 700; background: transparent; }}
QLabel#bfSysOk {{ color: {t.success}; font-size: {caption.size_px}px;
  font-weight: 600; background: transparent; }}

QFrame#bfSpecBar {{
  background: {t.bg_card}; border: 1px solid {t.border_soft};
  border-radius: {t.radius('md')}px;
}}
QLabel#bfSpecKey {{ color: {t.text_muted}; font-size: {caption.size_px}px;
  letter-spacing: 1px; background: transparent; }}
QLabel#bfSpecVal {{ color: {t.text_primary}; font-size: {h3.size_px}px;
  font-weight: 700; background: transparent; }}

QFrame#bfKpiCard {{
  background: {t.bg_card}; border: 1px solid {t.border_soft};
  border-radius: {t.radius('lg')}px;
  border-top: 2px solid {_rgba(bf_a, 0.25)};
}}
QFrame#bfKpiCard:hover {{
  border-top: 2px solid {bf_a};
  background: {_rgba(bf_a, 0.05)};
}}
QLabel#bfKpiHead {{ color: {t.text_secondary}; font-size: {caption.size_px}px;
  font-weight: 600; letter-spacing: 1px; background: transparent; }}
QLabel#bfKpiValue {{ color: {bf_a}; font-size: {display.size_px}px;
  font-weight: 800; background: transparent; }}
QLabel#bfKpiUnit {{ color: {t.text_primary}; font-size: {h3.size_px}px;
  background: transparent; }}
QPushButton#bfDropdown {{
  background: {t.bg_inset}; border: 1px solid {t.border_soft};
  color: {t.text_secondary}; border-radius: {t.radius('sm')}px;
  padding: 4px 10px; font-size: {caption.size_px}px;
}}
QPushButton#bfDropdown:hover {{ border-color: {bf_a}; color: {t.text_primary}; }}
QLabel#bfGranoLbl {{ color: {t.text_secondary}; font-size: {caption.size_px}px;
  background: transparent; }}
QLabel#bfGranoPct {{ color: {t.text_primary}; font-size: {caption.size_px}px;
  font-weight: 600; background: transparent; }}
QLabel#bfAlarms {{ color: {t.success}; font-size: {h2.size_px}px;
  font-weight: 700; background: transparent; }}

/* ===== banda warning fuentes (S8) ===== */
QFrame#staleBand {{
  background: {_rgba(t.warning, 0.12)};
  border: 1px solid {_rgba(t.warning, 0.5)};
  border-radius: {t.radius('sm')}px;
}}
QLabel#staleBandText {{ color: {t.warning}; font-size: {caption.size_px}px; background: transparent; }}

/* ===== scrollbars ===== */
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{
  width: 8px; background: transparent; margin: 0;
}}
QScrollBar::handle:vertical {{
  background: {t.border_soft}; border-radius: 4px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {t.text_muted}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
"""
