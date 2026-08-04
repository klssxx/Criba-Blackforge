from pathlib import Path

import pytest

from criba.ui.app_bridge import (
    BlackforgeLaunchError,
    resolve_blackforge_launch,
)


def test_development_launch_uses_current_interpreter_without_shell(
    tmp_path: Path,
) -> None:
    python = tmp_path / "python.exe"
    python.write_bytes(b"placeholder")

    spec = resolve_blackforge_launch(executable=str(python), frozen=False)

    assert spec.program == str(python.resolve())
    assert spec.arguments == ("-m", "criba.blackforge_gui")


def test_frozen_launch_is_allowlisted_sibling(tmp_path: Path) -> None:
    criba = tmp_path / "CRIBA.exe"
    blackforge = tmp_path / "BLACKFORGE.exe"
    criba.write_bytes(b"criba")
    blackforge.write_bytes(b"blackforge")

    spec = resolve_blackforge_launch(executable=str(criba), frozen=True)

    assert spec.program == str(blackforge.resolve())
    assert spec.arguments == ()
    assert Path(spec.program).parent == criba.resolve().parent


def test_frozen_launch_fails_closed_when_sibling_is_missing(tmp_path: Path) -> None:
    criba = tmp_path / "CRIBA.exe"
    criba.write_bytes(b"criba")

    with pytest.raises(BlackforgeLaunchError, match="No se encontró"):
        resolve_blackforge_launch(executable=str(criba), frozen=True)


def test_portable_spec_resolves_inputs_from_its_own_checkout() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    spec = (repo_root / "CRIBA-Blackforge.spec").read_text(encoding="utf-8")

    assert "ROOT = SPECPATH.replace" in spec
    assert "E:/PROYECTS/CRIBA" not in spec
