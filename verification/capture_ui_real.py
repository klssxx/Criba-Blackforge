"""Captura real de la GUI CRIBA (QPA windows, escritorio) a 1360x768 y 1680x1050.

Mismo flujo real que verification/smoke_ui_contract.py (S2->S3->S5 con engine
determinista, sin datos fake). Uso: python verification/capture_ui_real.py [outdir]
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from PySide6.QtCore import QThreadPool, QTimer
from PySide6.QtWidgets import QApplication

from criba.ui import actions
from criba.ui.main_window import CribaMainWindow

OUTDIR = sys.argv[1] if len(sys.argv) > 1 else "."
DB = os.path.join("artifacts", "capture_ui.sqlite3")
PROBLEM = ("Las organizaciones no detectan ni responden a amenazas avanzadas "
           "a tiempo, dejando ventanas de exposición críticas")


def main() -> int:
    if os.path.exists(DB):
        os.remove(DB)
    app = QApplication(sys.argv)
    win = CribaMainWindow(database=DB)
    # S2: problema base (mismo camino que smoke_ui_contract.py)
    win.problem = PROBLEM
    win.refs["stages"]["stageProblema"].set_state("done")
    win.refs["stages"]["stageGenerar"].set_state("active")
    win.refs["ideaTitle"].setText(PROBLEM)
    actions._set_buttons(win, {"navNuevaIdea": True, "navGenerar": True,
                               "navEvaluar": False, "navGuardar": False,
                               "navActualizar": True, "navHistorial": True,
                               "navBlackforge": True})
    # S3 + S5 con engine real
    actions.on_generar(win)
    QThreadPool.globalInstance().waitForDone(30000)
    app.processEvents()
    actions.on_evaluar(win)
    QThreadPool.globalInstance().waitForDone(30000)
    app.processEvents()
    assert win.packet is not None, "captura: packet real requerido"

    shots = [(1360, 768, "evidence_ui_final_1360.png"),
             (1680, 1050, "evidence_ui_final_1680.png")]

    def snap() -> None:
        if not shots:
            app.quit()
            return
        w, h, name = shots.pop(0)
        win.resize(w, h)
        QTimer.singleShot(700, lambda: _grab(name))

    def _grab(name: str) -> None:
        win.grab().save(os.path.join(OUTDIR, name))
        print("SAVED", name, win.size().width(), "x", win.size().height())
        snap()

    win.show()
    QTimer.singleShot(900, snap)
    rc = app.exec()
    if os.path.exists(DB):
        os.remove(DB)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
