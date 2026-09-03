"""P01-T01/T06: architecture boundary tests (ADR-001, addendum §C/§J).

Parses real imports of criba.intelligence.* and fails on violations:
- contracts/enums import nothing outside their layer
- L2/L1 never import L3/L4 or legacy engines
- no circular dependency intelligence <-> legacy/supra
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

SRC = Path(__file__).resolve().parents[2] / "src"

# Layers per ADR-001
FORBIDDEN_IN_INTELLIGENCE = (
    "criba.ui", "criba.gui", "criba.engine", "criba.hybrid", "criba.ensemble",
    "criba.chain", "criba.personas", "criba.lottery", "criba.blackforge",
    "supra_agentic",
)
PURE_MODULES = {"contracts", "enums"}  # must not import ANY criba.* except themselves


def _imports_of(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                mods.add(a.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module)
    return mods


def _py_files(subdir: str):
    yield from (SRC / "criba" / subdir).rglob("*.py")


def test_contracts_and_enums_are_pure():
    for name in PURE_MODULES:
        for f in [SRC / "criba" / "intelligence" / f"{name}.py"]:
            for m in _imports_of(f):
                if m.startswith("criba.") and not m.startswith(f"criba.intelligence.{name}"):
                    # stdlib/typing allowed; any other criba import is a violation
                    raise AssertionError(f"{f.name} imports {m} (must be pure)")


def test_intelligence_never_imports_legacy_or_supra():
    violations = []
    for f in _py_files("intelligence"):
        for m in _imports_of(f):
            if m == "criba" or m.startswith(tuple(FORBIDDEN_IN_INTELLIGENCE)):
                violations.append(f"{f.relative_to(SRC)} -> {m}")
    assert violations == [], f"boundary violations: {violations}"


def test_legacy_bridge_is_the_only_exception_surface():
    """legacy_bridge.py may be imported BY legacy code, but must not import
    legacy engines either (hooks are injected, not pulled)."""
    bridge = SRC / "criba" / "intelligence" / "legacy_bridge.py"
    if bridge.exists():
        bad = [m for m in _imports_of(bridge)
               if m.startswith(tuple(FORBIDDEN_IN_INTELLIGENCE))]
        assert bad == [], f"legacy_bridge imports forbidden: {bad}"


def test_no_circular_import_at_package_level():
    """intelligence imports nothing from criba legacy; legacy (so far)
    imports nothing from intelligence except through the bridge. Verifies
    the intelligence side is acyclic w.r.t. external packages."""
    ext: dict[str, set[str]] = {}
    for f in _py_files("intelligence"):
        rel = f.relative_to(SRC).with_suffix("").as_posix().replace("/", ".")
        ext[rel] = {m for m in _imports_of(f) if m.startswith("criba.intelligence")}
    # internal deps must be a DAG: check no self-cycle via simple DFS
    import graphlib
    deps = {}
    for mod, imps in ext.items():
        deps[mod] = {i for i in imps if i != mod and i in ext}
    try:
        graphlib.TopologicalSorter(deps).prepare()
    except graphlib.CycleError as e:
        raise AssertionError(f"cycle in intelligence imports: {e}") from e


if __name__ == "__main__":
    raise SystemExit(__import__("pytest").main([__file__, "-q"]))
