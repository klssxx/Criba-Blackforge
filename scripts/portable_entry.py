"""Portable CLI entry point for CRIBA + BLACKFORGE.

Forces UTF-8 stdio so accented Spanish output is not garbled by the
Windows console default code page (cp1252).
"""
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass

from criba.cli import main

raise SystemExit(main())
