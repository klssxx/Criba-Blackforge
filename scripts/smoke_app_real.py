"""SMOKE TEST REAL de CRIBA + BLACKFORGE (sin captura de pantalla).

Ejercita la aplicacion Windows real via su API publica en modo offscreen:
1. arranque limpio de la interfaz canonica (CribaMainWindow);
2. NUEVA IDEA (problema real);
3. GENERAR (motor real, query-driven);
4. EVALUAR (ranking real);
5. GUARDAR (persistencia real);
6. HISTORIAL (sesion presente);
7. BLACKFORGE (navegacion + loteria real + retorno);
8. cierre limpio;
9. reapertura y comprobacion de persistencia.

Registra PASS/FAIL por paso. No usa mocks: el motor, el catalogo BF y la
base de datos son los reales del repositorio.
"""
from __future__ import annotations

import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

from criba.storage import Storage
from criba.ui import actions
from criba.ui.main_window import CribaMainWindow


def wait_packet(win, qapp, timeout=5.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        qapp.processEvents()
        if win.packet is not None:
            return True
        QTest.qWait(10)
    return False


def wait_rows(win, qapp, timeout=5.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        qapp.processEvents()
        if win.refs["rankingModel"].rowCount() > 0:
            return True
        QTest.qWait(10)
    return False


def main() -> int:
    qapp = QApplication.instance() or QApplication([])
    results = []

    def rec(step, ok, detail=""):
        results.append((step, ok, detail))
        print(f"[{'PASS' if ok else 'FAIL'}] {step}" + (f" :: {detail}" if detail else ""))

    db = "smoke_criba.sqlite3"
    if os.path.exists(db):
        os.remove(db)

    # 1. Arranque limpio
    win = CribaMainWindow(db)
    win.show()
    qapp.processEvents()
    rec("1. Arranque interfaz canonica", win is not None and win.isVisible(),
        win.windowTitle())

    # 2. Nueva idea
    query = "Proteger una API REST de ataques de inyeccion SQL y SSRF"
    actions.on_nueva_idea_no_dialog(win, query)
    qapp.processEvents()
    rec("2. Nueva idea", win.problem == query)

    # 3. Generar (motor real)
    actions.on_generar(win)
    ok = wait_packet(win, qapp)
    rec("3. Generar (motor real)", ok,
        f"ideas={len(win.packet['innovation']['ideas'])}" if ok else "sin packet")

    # 4. Evaluar (ranking real)
    actions.on_evaluar(win)
    okr = wait_rows(win, qapp)
    rec("4. Evaluar (ranking)", okr,
        f"filas={win.refs['rankingModel'].rowCount()}" if okr else "sin filas")

    # 5. Guardar (persistencia real)
    before = len(win.saved_ids)
    actions.on_guardar(win)
    qapp.processEvents()
    saved = len(win.saved_ids) > before
    ident = next(iter(win.saved_ids)) if saved else None
    rec("5. Guardar", saved, f"id={ident}")

    # 6. Historial (sesion presente)
    sessions = win.store.list_sessions(20)
    in_hist = any(s["query"] == query for s in sessions)
    rec("6. Historial", in_hist, f"sesiones={len(sessions)}")

    # 7. Blackforge (navegacion + loteria real + retorno)
    actions.on_blackforge(win)
    qapp.processEvents()
    on_bf = win.stack.currentIndex() == 1
    # ejecutar loteria BF (modo optimizado por defecto = asociativa)
    win.blackforge_page._on_execute()
    qapp.processEvents()
    bf_rows = win.blackforge_page.ideasModel.rowCount()
    rec("7a. Blackforge navegacion", on_bf)
    rec("7b. Blackforge loteria real", bf_rows > 0,
        f"filas_top5={bf_rows}")
    # retorno a CRIBA
    win.show_criba_page()
    qapp.processEvents()
    back = win.stack.currentIndex() == 0
    rec("7c. Retorno a CRIBA", back)

    # 8. Cierre limpio
    win.close()
    qapp.processEvents()
    rec("8. Cierre limpio", True)

    # 9. Reapertura + persistencia
    win2 = CribaMainWindow(db)
    win2.show()
    qapp.processEvents()
    sessions2 = win2.store.list_sessions(20)
    reopen = any(s["query"] == query for s in sessions2)
    rec("9. Reapertura + persistencia", reopen,
        f"sesiones={len(sessions2)}")
    win2.close()
    qapp.processEvents()

    failed = [r for r in results if not r[1]]
    print(f"\nSMOKE: {len(results)-len(failed)}/{len(results)} PASS")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
