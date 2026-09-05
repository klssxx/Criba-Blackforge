"""Functional-decomposition and mechanism-search hypotheses (P09 / T062-T063)."""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..contracts import EvidenceDocument, InventionCandidate


def _normalized_functions(
    component_functions: Mapping[str, Sequence[str]],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Return explicit component/function pairs without inferring missing ones."""

    normalized: list[tuple[str, tuple[str, ...]]] = []
    for raw_component, raw_functions in component_functions.items():
        component = str(raw_component).strip()
        if not component:
            continue
        if isinstance(raw_functions, str) or not isinstance(raw_functions, (list, tuple, set)):
            return ()
        functions = tuple(
            sorted({str(function).strip() for function in raw_functions if str(function).strip()})
        )
        if not functions:
            return ()
        normalized.append((component, functions))
    return tuple(sorted(normalized))


def decompose_functional_hypotheses(
    problem: str,
    component_functions: Mapping[str, Sequence[str]],
    *,
    limit: int = 20,
) -> list[InventionCandidate]:
    """Produce capped T062 prompts for functions explicitly assigned to components.

    A decomposition exposes caller-supplied function boundaries. It does not
    identify a mechanism, infer omitted functions, or establish that the
    supplied decomposition is complete or correct.
    """

    normalized_problem = problem.strip()
    if not normalized_problem:
        raise ValueError("problem must not be empty")
    if limit < 0:
        raise ValueError("limit must not be negative")
    if not isinstance(component_functions, Mapping):
        raise TypeError("component_functions must map components to function sequences")

    normalized_functions = _normalized_functions(component_functions)
    if not normalized_functions or limit == 0:
        return []

    candidates: list[InventionCandidate] = []
    for component, functions in normalized_functions:
        for function in functions:
            candidates.append(
                InventionCandidate(
                    title=f"Function: {component} → {function}",
                    description=(
                        f"T062 functional-decomposition hypothesis for {normalized_problem}: "
                        f"{component} is explicitly assigned {function}. This is not evidence "
                        "that the function is complete, correct, feasible, or novel."
                    ),
                    operators=("T062",),
                )
            )
            if len(candidates) == limit:
                return candidates
    return candidates


def _normalized_requested_functions(functions: Sequence[str]) -> tuple[str, ...]:
    if isinstance(functions, str) or not isinstance(functions, (list, tuple, set)):
        raise TypeError("functions must be a sequence of function names")
    return tuple(sorted({str(function).strip() for function in functions if str(function).strip()}))


def search_function_to_mechanism_hypotheses(
    problem: str,
    functions: Sequence[str],
    documents: Sequence[EvidenceDocument],
    *,
    limit: int = 20,
) -> list[InventionCandidate]:
    """Return T063 hypotheses only from explicit retrieved function/mechanism data.

    Retrieval is deliberately outside this function: callers supply documents
    returned by an IIE retriever. A document contributes only when its metadata
    contains a ``function_mechanisms`` mapping from function name to mechanism
    names; prose and unrelated metadata are not inferred.
    """

    normalized_problem = problem.strip()
    if not normalized_problem:
        raise ValueError("problem must not be empty")
    if limit < 0:
        raise ValueError("limit must not be negative")
    requested = _normalized_requested_functions(functions)
    if not requested or limit == 0:
        return []
    if isinstance(documents, str) or not isinstance(documents, (list, tuple, set)):
        raise TypeError("documents must be a sequence of EvidenceDocument values")

    requested_by_key = {function.casefold(): function for function in requested}
    records: set[tuple[str, str, str]] = set()
    for document in documents:
        if not isinstance(document, EvidenceDocument):
            raise TypeError("documents must contain EvidenceDocument values")
        raw_mapping = (document.metadata or {}).get("function_mechanisms")
        if not isinstance(raw_mapping, Mapping):
            continue
        for raw_function, raw_mechanisms in raw_mapping.items():
            function = str(raw_function).strip()
            requested_function = requested_by_key.get(function.casefold())
            if not requested_function:
                continue
            if isinstance(raw_mechanisms, str) or not isinstance(raw_mechanisms, (list, tuple, set)):
                continue
            for raw_mechanism in raw_mechanisms:
                mechanism = str(raw_mechanism).strip()
                if mechanism:
                    records.add((requested_function, mechanism, document.doc_id))

    candidates: list[InventionCandidate] = []
    for function, mechanism, doc_id in sorted(records):
        candidates.append(
            InventionCandidate(
                title=f"Mechanism: {function} → {mechanism}",
                description=(
                    f"T063 function-to-mechanism hypothesis for {normalized_problem}: "
                    f"retrieved document {doc_id} explicitly maps {function} to {mechanism}. "
                    "This is a retrieval lead, not evidence that the mechanism solves the "
                    "problem or is feasible, novel, or complete."
                ),
                mechanism=mechanism,
                operators=("T063",),
            )
        )
        if len(candidates) == limit:
            break
    return candidates
