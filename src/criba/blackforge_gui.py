"""Punto de entrada de la aplicación de escritorio BLACKFORGE.

Entrada ligera al mismo motor que CRIBA (mandato §5): no tiene estado ni
lógica propios; solo construye ``BlackforgeWindow``. Las rutas de
arranque que lo referencian son ``python -m criba.blackforge_gui``
(``app_bridge.resolve_blackforge_launch`` en desarrollo) y el punto de
entrada de PyInstaller ``scripts/blackforge_entry_gui.py``.
"""
from __future__ import annotations

import os
import sys


def run(database=None, query: str = "") -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print(
            "PySide6 no está instalado. Ejecute 'uv sync --extra gui --locked' "
            "para usar 'criba blackforge-gui'.",
            file=sys.stderr,
        )
        return 2

    from .ui.blackforge_window import BlackforgeWindow

    app = QApplication.instance() or QApplication(sys.argv)
    window = BlackforgeWindow(database, query=query)
    window.show()
    smoke_exit_ms = os.environ.get("CRIBA_SMOKE_EXIT_MS")
    if smoke_exit_ms:
        from PySide6.QtCore import QTimer

        QTimer.singleShot(max(0, int(smoke_exit_ms)), window.close)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
