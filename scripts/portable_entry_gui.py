"""Portable GUI entry point for CRIBA + BLACKFORGE.

Launches the PySide6 desktop window directly (double-click friendly, no console).
Falls back to a clear error if PySide6 is unavailable.
"""
from criba.gui import run

raise SystemExit(run())
