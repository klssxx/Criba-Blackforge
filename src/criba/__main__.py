"""Entry point for ``python -m criba``.

Historically ``python -m criba`` failed with "No module named criba.__main__".
This module makes the package directly runnable. With no arguments it launches
the GUI (the primary Windows application); any arguments are forwarded to the
full CLI (``criba.cli.main``), so ``python -m criba blackforge --help`` etc.
keep working.
"""
from __future__ import annotations

import sys

from .cli import main


def _run() -> int:
    argv = sys.argv[1:]
    if not argv:
        # No subcommand: launch the desktop GUI (canonical Windows app).
        argv = ["gui"]
    return main(argv)


if __name__ == "__main__":
    raise SystemExit(_run())
