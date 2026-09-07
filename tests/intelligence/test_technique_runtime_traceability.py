"""Trazabilidad runtime del registro T001-T130.

Un estado IMPLEMENTED debe corresponder a código real: cada referencia de
`implementation` debe importar (módulo y/o funciones) y cada nombre de test
declarado debe existir como función en tests/. El defecto que motiva este
guard: el commit cbac469 eliminó los módulos invention/* (~5.1k líneas) y el
registro siguió declarando 11 técnicas IMPLEMENTED sobre código borrado.
"""
from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from criba.intelligence.registry import TechniqueRegistry

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "data" / "intelligence" / "technique_registry.yaml"


def _expand_implementation(implementation: str) -> list[str]:
    """Referencias del registro → rutas punteadas resolubles.

    Formatos históricos: 'pkg.mod.func', 'pkg.mod.f1/f2' (el segmento
    sin punto hereda el prefijo del anterior, hasta su último punto) y
    'pkg.{m1,m2}' (dos módulos con prefijo común).
    """
    refs: list[str] = []
    for part in implementation.split("/"):
        part = part.strip()
        if not part:
            continue
        if "{" in part:
            prefix, rest = part.split("{", 1)
            for piece in rest.rstrip("}").split(","):
                refs.append(prefix + piece.strip())
        elif "." not in part and refs:
            refs.append(refs[-1].rsplit(".", 1)[0] + "." + part)
        else:
            refs.append(part)
    return refs


def _ref_resolves(dotted: list[str]) -> bool:
    """Importa el prefijo-módulo más largo y resuelve el resto como atributos."""
    for i in range(len(dotted), 0, -1):
        try:
            module = importlib.import_module(".".join(dotted[:i]))
        except ModuleNotFoundError:
            continue
        obj = module
        for segment in dotted[i:]:
            obj = getattr(obj, segment, None)
            if obj is None:
                return False
        return True
    return False


def _test_function_names() -> set[str]:
    names: set[str] = set()
    tests_root = Path(__file__).resolve().parents[2] / "tests"
    for path in tests_root.rglob("test_*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names |= {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test")
        }
    return names


def test_implemented_techniques_resolve_to_real_code():
    """IMPLEMENTED ⇒ implementation importa y tests existen (§110 con dientes)."""
    registry = TechniqueRegistry(REGISTRY_PATH)
    implemented = registry.implemented()
    test_names = _test_function_names()
    for technique in implemented:
        assert technique.implementation, f"{technique.id}: IMPLEMENTED sin implementation"
        for ref in _expand_implementation(technique.implementation):
            assert _ref_resolves(ref.split(".")), (
                f"{technique.id}: la referencia '{ref}' no importa — el registro "
                "declara una capacidad sobre código inexistente"
            )
        for declared in technique.tests:
            assert declared in test_names, (
                f"{technique.id}: el test declarado '{declared}' no existe en tests/"
            )


def test_planned_techniques_do_not_claim_implementation():
    """PLANNED ⇒ implementation null. Un registro no puede declarar código que
    no existe; la ausencia de ficha nunca se sustituye por contenido inventado."""
    registry = TechniqueRegistry(REGISTRY_PATH)
    for technique in registry.all():
        if technique.status == "PLANNED":
            assert technique.implementation is None, (
                f"{technique.id}: PLANNED con implementation no nula"
            )


def test_reference_resolver_accepts_all_historical_formats():
    """El resolutor cubre los formatos históricos del generador."""
    assert _expand_implementation("pkg.mod.func") == ["pkg.mod.func"]
    assert _expand_implementation("pkg.mod.f1/f2") == ["pkg.mod.f1", "pkg.mod.f2"]
    assert _expand_implementation("pkg.{m1, m2}") == ["pkg.m1", "pkg.m2"]
    # un módulo real del árbol resuelve completo y por función:
    assert _ref_resolves(["criba", "intelligence", "prior_art", "mutation_loop"])
    assert _ref_resolves(
        ["criba", "intelligence", "prior_art", "mutation_loop", "MutationResult"]
    )
    assert not _ref_resolves(["criba", "intelligence", "modulo_que_no_existe"])


if __name__ == "__main__":
    raise SystemExit(__import__("pytest").main([__file__, "-q"]))
