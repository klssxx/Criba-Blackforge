from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PORTABLE_DOCS = (
    "FIRST_RUN_ES.md",
    "FIRST_RUN_EN.md",
    "THIRD_PARTY_NOTICES.md",
    "LICENSE",
)


def test_portable_build_includes_user_facing_documents() -> None:
    build_script = (ROOT / "scripts" / "build-portable.ps1").read_text(
        encoding="utf-8"
    )

    for filename in PORTABLE_DOCS:
        assert (ROOT / filename).is_file()
        assert f"'{filename}'" in build_script


def test_readme_describes_the_separated_local_runtime() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Motor local y determinista" in readme
    assert "scripts\\launch_workbench.bat" in readme
    assert "SUPRA_AGENTIC" not in readme
    assert "api/v1" not in readme
