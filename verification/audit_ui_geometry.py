"""Auditoría determinista de clipping/overflow de la GUI CRIBA.

Para 1360x768 y 1680x1050 comprueba con geometrías reales de Qt:
- los 6 segmentos del footer visibles y dentro de la ventana;
- sidebar completo; sin scroll horizontal en los QScrollArea;
- topbar sin desbordar; tabla de ranking dentro del viewport.
Uso: python verification/audit_ui_geometry.py   (plataforma nativa real;
     exportar QT_QPA_PLATFORM=offscreen solo para CI sin escritorio)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from PySide6.QtCore import QPoint, QThreadPool
from PySide6.QtWidgets import QApplication, QScrollArea

from criba.ui import actions
from criba.ui.main_window import CribaMainWindow

DB = os.path.join("artifacts", "audit_geo.sqlite3")
PROBLEM = ("Las organizaciones no detectan ni responden a amenazas avanzadas "
           "a tiempo, dejando ventanas de exposición críticas")

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("OK  " if cond else "FAIL") + " " + msg)
    if not cond:
        failures.append(msg)


def in_window(win, widget, name: str, res: str) -> None:
    if not widget.isVisible():
        check(False, f"{res}: {name} NO visible")
        return
    tl = widget.mapTo(win, QPoint(0, 0))
    r = tl.x() + widget.width()
    b = tl.y() + widget.height()
    check(tl.x() >= 0 and tl.y() >= 0 and r <= win.width() and b <= win.height(),
          f"{res}: {name} dentro de ventana (x={tl.x()},y={tl.y()},r={r},b={b})")


def audit(win, res: str) -> None:
    QApplication.processEvents()
    for key, seg in win.footerSegs.items():
        in_window(win, seg, f"footer {key}", res)
    for key, btn in win.nav.items():
        in_window(win, btn, f"nav {key}", res)
    in_window(win, win.greetingTitle, "greetingTitle", res)
    in_window(win, win.timeLabel, "timeLabel", res)
    for sa in win.findChildren(QScrollArea):
        hbar = sa.horizontalScrollBar()
        check(hbar.maximum() == 0,
              f"{res}: {sa.objectName()} sin scroll horizontal (max={hbar.maximum()})")
    table = win.refs["rankingTable"]
    if table.isVisible():
        need = sum(table.columnWidth(c) for c in range(table.model().columnCount()))
        check(need <= table.viewport().width() + 2,
              f"{res}: columnas ranking caben ({need} <= {table.viewport().width()})")


def main() -> int:
    if os.path.exists(DB):
        os.remove(DB)
    app = QApplication.instance() or QApplication([])
    win = CribaMainWindow(database=DB)
    win.problem = PROBLEM
    win.refs["ideaTitle"].setText(PROBLEM)
    actions._set_buttons(win, {"navNuevaIdea": True, "navGenerar": True,
                               "navEvaluar": False, "navGuardar": False,
                               "navActualizar": True, "navHistorial": True,
                               "navBlackforge": True})
    actions.on_generar(win)
    QThreadPool.globalInstance().waitForDone(30000)
    app.processEvents()
    actions.on_evaluar(win)
    QThreadPool.globalInstance().waitForDone(30000)
    app.processEvents()
    win.show()
    for w, h in ((1360, 768), (1680, 1050)):
        win.resize(w, h)
        app.processEvents()
        audit(win, f"{w}x{h}")
    win.close()
    if os.path.exists(DB):
        os.remove(DB)
    print("GEOMETRY_AUDIT_" + ("FAIL" if failures else "ALL_OK"))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
