"""IIE TechniqueRegistry (P01-T05, addendum §104-§116).

Loads data/intelligence/technique_registry.yaml as the single machine-readable
source of truth for T001-T130. No execution here — TechniqueExecutor arrives
with its phase; this module only describes/queries capabilities.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .enums import TechniqueStatus

_VALID_OWNERS = {"CRIBA", "CRIBA_IIE", "BLACKFORGE", "SUPRA_ORCHESTRATION", "CRIBA_PLUS_SUPRA", "CRIBA_PLUS_IIE"}
_VALID_STATUSES = {s.value for s in TechniqueStatus}


@dataclass(frozen=True)
class Technique:
    id: str
    name: str
    family: str
    owner: str
    module: tuple[str, ...]
    phase: tuple[str, ...]
    pipelines: tuple[str, ...]
    model_default: str
    model_reasoning: str
    cost_class: str
    requires_network: bool
    requires_credentials: bool
    status: str
    implementation: str | None
    input_contracts: tuple[str, ...]
    output_contracts: tuple[str, ...]
    tests: tuple[str, ...]
    subtechniques: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        d = {
            "id": self.id, "name": self.name, "family": self.family, "owner": self.owner,
            "module": list(self.module), "phase": list(self.phase),
            "pipelines": list(self.pipelines), "model": {"default": self.model_default,
            "reasoning": self.model_reasoning}, "cost_class": self.cost_class,
            "requires_network": self.requires_network,
            "requires_credentials": self.requires_credentials,
            "status": self.status, "implementation": self.implementation,
            "input_contracts": list(self.input_contracts),
            "output_contracts": list(self.output_contracts),
            "tests": list(self.tests),
        }
        if self.subtechniques:
            d["subtechniques"] = list(self.subtechniques)
        return d


def _default_registry_path() -> Path:
    # registry.py lives inside src/criba/intelligence; the registry data ships
    # under the CRIBA data root (portable bundle, checkout or installed wheel).
    from criba.constants import DATA_ROOT

    return DATA_ROOT / "intelligence" / "technique_registry.yaml"


class TechniqueRegistry:
    """Read-only view over technique_registry.yaml (§105 machine-readable)."""

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else _default_registry_path()
        self._techniques: dict[str, Technique] = {}
        self._load()

    def _load(self) -> None:
        import yaml  # lazy: pyyaml is already a CRIBA dependency

        raw = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError(f"registry must be a YAML list: {self.path}")
        for item in raw:
            model = item.get("model") or {}
            t = Technique(
                id=item["id"], name=item["name"], family=item["family"],
                owner=item["owner"],
                module=tuple(item.get("module") or ()),
                phase=tuple(item.get("phase") or ()),
                pipelines=tuple(item.get("pipelines") or ()),
                model_default=model.get("default", "GLM-5.3"),
                model_reasoning=model.get("reasoning", "high"),
                cost_class=item.get("cost_class", "FREE_NETWORK"),
                requires_network=bool(item.get("requires_network", False)),
                requires_credentials=bool(item.get("requires_credentials", False)),
                status=item.get("status", "PLANNED"),
                implementation=item.get("implementation"),
                input_contracts=tuple(item.get("input_contracts") or ()),
                output_contracts=tuple(item.get("output_contracts") or ()),
                tests=tuple(item.get("tests") or ()),
                subtechniques=tuple(item.get("subtechniques") or ()),
            )
            if t.id in self._techniques:
                raise ValueError(f"duplicate technique id: {t.id}")
            self._techniques[t.id] = t

    # -- queries -----------------------------------------------------------
    def get(self, technique_id: str) -> Technique:
        return self._techniques[technique_id]

    def all(self) -> list[Technique]:
        return [self._techniques[k] for k in sorted(self._techniques)]

    def by_family(self, family: str) -> list[Technique]:
        return [t for t in self.all() if t.family == family]

    def by_pipeline(self, pipeline: str) -> list[Technique]:
        return [t for t in self.all() if pipeline in t.pipelines]

    def by_phase(self, phase: str) -> list[Technique]:
        return [t for t in self.all() if phase in t.phase]

    def by_owner(self, owner: str) -> list[Technique]:
        return [t for t in self.all() if t.owner == owner]

    def implemented(self) -> list[Technique]:
        return [t for t in self.all() if t.status.startswith("IMPLEMENTED")]

    def count(self) -> int:
        return len(self._techniques)

    # -- integrity checks (§106-§113) --------------------------------------
    def validate(self) -> list[str]:
        errors: list[str] = []
        expected = [f"T{i:03d}" for i in range(1, 131)]
        ids = [t.id for t in self.all()]
        if len(ids) != 130:
            errors.append(f"count={len(ids)} != 130")
        missing = set(expected) - set(ids)
        extra = set(ids) - set(expected)
        if missing:
            errors.append(f"missing={sorted(missing)}")
        if extra:
            errors.append(f"extra={sorted(extra)}")
        for t in self.all():
            if t.owner not in _VALID_OWNERS:
                errors.append(f"{t.id}: unknown owner {t.owner}")
            if t.status not in _VALID_STATUSES:
                errors.append(f"{t.id}: invalid status {t.status}")
            if not t.pipelines:
                errors.append(f"{t.id}: orphan (no execution pipeline)")
            if not t.module:
                errors.append(f"{t.id}: no module")
            if not t.phase:
                errors.append(f"{t.id}: no phase")
            if not t.tests:
                errors.append(f"{t.id}: no tests")
            if t.status == "IMPLEMENTED" and not t.implementation:
                errors.append(f"{t.id}: IMPLEMENTED without implementation ref")
            if t.status == "IMPLEMENTED" and not t.tests:
                errors.append(f"{t.id}: IMPLEMENTED without tests")
        return errors
