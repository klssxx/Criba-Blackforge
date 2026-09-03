"""Executable registry for blueprint-declared invention operators (P09-T02)."""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from ..contracts import InventionCandidate
from .taxonomy import OPERATORS_BY_KEY, OperatorDefinition


@dataclass(frozen=True)
class OperatorContext:
    """Evidence-bounded input shared by invention operator implementations."""

    problem: str
    evidence_doc_ids: tuple[str, ...] = ()
    gap_ids: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()


OperatorHandler = Callable[[OperatorContext], Iterable[InventionCandidate]]


@dataclass
class OperatorRegistry:
    """Registry that prevents undeclared or untraceable operator execution."""

    _handlers: dict[str, OperatorHandler] = field(default_factory=dict)

    def definition(self, key: str) -> OperatorDefinition:
        definition = OPERATORS_BY_KEY.get(key)
        if definition is None:
            raise KeyError(f"unknown invention operator: {key}")
        return definition

    def register(self, key: str, handler: OperatorHandler) -> None:
        self.definition(key)
        if key in self._handlers:
            raise ValueError(f"operator already registered: {key}")
        self._handlers[key] = handler

    def registered_keys(self) -> tuple[str, ...]:
        return tuple(sorted(self._handlers))

    def execute(self, key: str, context: OperatorContext) -> list[InventionCandidate]:
        definition = self.definition(key)
        handler = self._handlers.get(key)
        if handler is None:
            raise LookupError(f"operator has no registered handler: {key}")
        candidates = list(handler(context))
        for candidate in candidates:
            if not isinstance(candidate, InventionCandidate):
                raise TypeError("operator handlers must yield InventionCandidate values")
            if not set(definition.technique_ids).issubset(candidate.operators):
                raise ValueError(
                    f"candidate {candidate.candidate_id} is missing technique traceability "
                    f"for {key}"
                )
        return candidates
