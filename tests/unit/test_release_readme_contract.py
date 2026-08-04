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


def test_readme_has_direct_download_and_real_screenshots() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert (
        "releases/latest/download/"
        "CRIBA-Blackforge-Portable-Windows-x64.zip"
    ) in readme

    for filename in ("criba-overview.png", "blackforge-overview.png"):
        image = ROOT / "docs" / "assets" / filename
        assert image.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        assert image.stat().st_size > 50_000
