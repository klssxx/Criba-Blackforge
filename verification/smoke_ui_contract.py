"""Smoke offscreen de la nueva pantalla CRIBA (contrato UI).

Valida: instanciación, S1, flujo S2->S3->S5->S6 con engine real,
y que el contenido del problema sobrevive (no solo estructura).
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, "src")

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QApplication

from criba.ui.main_window import CribaMainWindow
from criba.ui import actions

app = QApplication.instance() or QApplication([])
win = CribaMainWindow("artifacts/smoke_ui.sqlite3")
win.show()
app.processEvents()

# ---- S1 ----
assert win.nav["navGenerar"].isEnabled() is False, "S1: Generar debe estar OFF"
assert win.nav["navEvaluar"].isEnabled() is False, "S1: Evaluar debe estar OFF"
assert win.nav["navGuardar"].isEnabled() is False, "S1: Guardar debe estar OFF"
assert win.nav["navNuevaIdea"].isEnabled(), "S1: Nueva idea ON"
assert win.refs["scoreGauge"].isHidden(), "S1: gauge oculto"
assert win.footerSegs["fsIdeas"]._val.text() == "0"
print("S1 OK")

# ---- S2 (sin diálogo: set directo del problema) ----
PROBLEM = "Reducir el tiempo de auditoría de dependencias en pipelines CI locales"
win.problem = PROBLEM
win.refs["stages"]["stageProblema"].set_state("done")
win.refs["stages"]["stageGenerar"].set_state("active")
win.refs["ideaTitle"].setText(PROBLEM)
actions._set_buttons(win, {"navNuevaIdea": True, "navGenerar": True,
                           "navEvaluar": False, "navGuardar": False,
                           "navActualizar": True, "navHistorial": True,
                           "navBlackforge": True})
assert win.nav["navGenerar"].isEnabled(), "S2: Generar ON"
print("S2 OK")

# ---- S3 -> generado (engine real, síncrono en el pool) ----
actions.on_generar(win)
QThreadPool.globalInstance().waitForDone(30000)
app.processEvents()
assert win.packet is not None, "S3: packet real generado"
assert win.packet["original_query"] == PROBLEM, "CONTENIDO: query sobrevive"
ideas = win.packet["innovation"]["ideas"]
assert len(ideas) >= 8, f"S3: >=8 ideas reales, hay {len(ideas)}"
assert win.refs["stages"]["stageGenerar"].state() == "done"
assert win.nav["navEvaluar"].isEnabled(), "S3->S4: Evaluar ON"
print(f"S3 OK ({len(ideas)} ideas)")

# ---- S4 -> S5 ----
actions.on_evaluar(win)
QThreadPool.globalInstance().waitForDone(30000)
app.processEvents()
assert not win.refs["rankingTable"].isHidden(), "S5: tabla visible"
model = win.refs["rankingModel"]
assert model.rowCount() == len(ideas), "S5: filas = ideas"
best_score = win.packet["innovation"]["ideas"][0]["convergence"]["value_score"]
shown = win.refs["mBestScore"]._value.text()
assert shown == f"{best_score:.2f}", f"S5: best score visible {shown} vs {best_score}"
# CONTENIDO: los títulos del ranking provienen del engine, no placeholders
from criba.ui.ranking import COL_IDEA
first_title = model.data(model.index(0, COL_IDEA))
assert first_title and first_title != "—", "S5: título real en ranking"
assert win.footerSegs["fsSesion"]._val.text().startswith("CRB-"), "S5: footer sesión"
print(f"S5 OK (best={best_score})")

# ---- S6 ----
actions.on_guardar(win)
app.processEvents()
assert len(win.saved_ids) == 1, "S6: guardado en SQLite"
from criba.storage import Storage
persisted = Storage("artifacts/smoke_ui.sqlite3").get(next(iter(win.saved_ids)))
assert persisted["query"] == PROBLEM, "CONTENIDO: query persistida intacta"
assert win.nav["navGuardar"].isEnabled() is False, "S6: Guardar OFF tras guardar"
print("S6 OK (persistencia verificada)")

# ---- S8 fuentes ----
actions.on_actualizar(win)
QThreadPool.globalInstance().waitForDone(15000)
app.processEvents()
assert win.sources_updated_at is not None, "S8: timestamp de fuentes"
assert win.footerSegs["fsFuentes"]._val.text().startswith("Hace"), "S8: frescura ok"
print("S8 OK")

# ---- S9 error controlado ----
actions.on_operation_error(win, "navGenerar", "stageGenerar", "motor no disponible")
app.processEvents()
assert not win.errorBanner.isHidden(), "S9: banner visible"
assert win.refs["stages"]["stageGenerar"].state() == "error"
print("S9 OK")

win.close()
app.processEvents()
print("SMOKE_UI_ALL_OK")
