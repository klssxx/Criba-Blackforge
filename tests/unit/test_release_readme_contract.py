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
    readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_es = (ROOT / "README.es.md").read_text(encoding="utf-8")
    assert "scripts\\launch_workbench.bat" in readme_en
    assert "Motor local y determinista" in readme_es
    assert "SUPRA_AGENTIC" not in readme_en
    assert "SUPRA_AGENTIC" not in readme_es
    assert "api/v1" not in readme_en
    assert "api/v1" not in readme_es
