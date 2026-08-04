"""Standalone BLACKFORGE desktop application entry point."""
from __future__ import annotations

import sys
from typing import Any


def run(database: Any = None) -> int:
    """Launch BLACKFORGE as its own application and event loop."""

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print(
            "PySide6 no está instalado. Instala el extra 'gui' para usar BLACKFORGE.",
            file=sys.stderr,
        )
        return 2

    from .ui.blackforge_window import BlackforgeWindow

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("BLACKFORGE")
    app.setOrganizationName("CRIBA")
    window = BlackforgeWindow(database=database)
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
