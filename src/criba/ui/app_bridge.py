"""Secure process boundary between the CRIBA and BLACKFORGE desktop apps.

The two interfaces deliberately run as different processes.  This module only
builds trusted executable/argument pairs; it never interpolates a command line
or invokes a shell.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BlackforgeLaunchSpec:
    """Executable and argv used by ``QProcess`` to start BLACKFORGE."""

    program: str
    arguments: tuple[str, ...]


class BlackforgeLaunchError(RuntimeError):
    """Raised when the packaged BLACKFORGE executable cannot be resolved."""


def resolve_blackforge_launch(
    *,
    executable: str | None = None,
    frozen: bool | None = None,
) -> BlackforgeLaunchSpec:
    """Return a shell-free, allowlisted launch specification.

    Development launches the installed module with the current interpreter.
    A PyInstaller build launches the sibling ``BLACKFORGE.exe`` and rejects
    any path that escapes the directory containing the CRIBA executable.
    """

    running_executable = Path(executable or sys.executable).resolve()
    is_frozen = bool(getattr(sys, "frozen", False) if frozen is None else frozen)

    if not is_frozen:
        if not running_executable.is_file():
            raise BlackforgeLaunchError(
                f"El intérprete de Python no existe: {running_executable}"
            )
        return BlackforgeLaunchSpec(
            program=str(running_executable),
            arguments=("-m", "criba.blackforge_gui"),
        )

    candidate = running_executable.with_name("BLACKFORGE.exe").resolve()
    if candidate.parent != running_executable.parent:
        raise BlackforgeLaunchError("La ruta de BLACKFORGE salió del directorio permitido.")
    if candidate.name.casefold() != "blackforge.exe":
        raise BlackforgeLaunchError("Nombre de ejecutable BLACKFORGE no permitido.")
    if not candidate.is_file():
        raise BlackforgeLaunchError(
            f"No se encontró el ejecutable hermano: {candidate}"
        )
    return BlackforgeLaunchSpec(program=str(candidate), arguments=())
