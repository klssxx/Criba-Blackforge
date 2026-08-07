"""Standalone BLACKFORGE desktop application entry point."""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any


def _launch_query(argv: list[str]) -> str:
    """Read the optional CRIBA problem passed over the shell-free process boundary."""

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--query", default="")
    parsed, _ = parser.parse_known_args(argv)
    return str(parsed.query)[:20_000]


def run(database: Any = None, query: str | None = None) -> int:
    """Launch BLACKFORGE as its own application and event loop."""

    try:
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print(
            "PySide6 no está instalado. Instala el extra 'gui' para usar BLACKFORGE.",
            file=sys.stderr,
        )
        return 2

    from .ui.blackforge_window import BlackforgeWindow

    active_query = _launch_query(sys.argv[1:]) if query is None else query
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("BLACKFORGE")
    app.setOrganizationName("CRIBA")
    window = BlackforgeWindow(database=database, query=active_query)
    window.showMaximized()
    smoke_exit_ms = os.environ.get("CRIBA_SMOKE_EXIT_MS")
    if smoke_exit_ms:
        QTimer.singleShot(max(0, int(smoke_exit_ms)), window.close)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
