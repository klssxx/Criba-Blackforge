"""Frozen GUI entry point for the CRIBA + BLACKFORGE portable build.

Launches the PySide6 desktop application directly (no CLI subcommand needed).
Kept separate from ``portable_entry.py`` (CLI) so the packaged executable is a
windowed GUI app rather than a console tool.
"""
import sys

from criba.gui import run

if __name__ == "__main__":
    raise SystemExit(run())
