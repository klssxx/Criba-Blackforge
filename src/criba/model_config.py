"""Persistent local-model profiles shared by CRIBA and BLACKFORGE.

The configuration deliberately stores no API secrets.  Both desktop
executables read the same JSON file from the user's application-data folder,
so a GGUF profile configured in either interface is immediately available to
the other one.
"""

from __future__ import annotations

import json
import math
import os
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

BackendKind = Literal["llama_cpp", "ollama"]
ReasoningLevel = Literal["fast", "balanced", "deep"]


def _text(value: Any, default: str, *, limit: int) -> str:
    """Return bounded JSON text without coercing containers into strings."""

    if not isinstance(value, str):
        return default
    cleaned = value.strip()
    return (cleaned or default)[:limit]


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return max(minimum, min(maximum, parsed))


def _bounded_float(value: Any, default: float, minimum: float, maximum: float) -> float:
    if isinstance(value, bool):
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    if not math.isfinite(parsed):
        return default
    return max(minimum, min(maximum, parsed))


def model_config_path() -> Path:
    """Return the overrideable, user-writable model configuration path."""

    override = os.environ.get("CRIBA_MODEL_CONFIG")
    if override:
        return Path(override).expanduser()
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "CRIBA-Blackforge"
    return base / "models.json"


@dataclass
class ModelProfile:
    """One local inference profile selectable by both desktop applications."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Modelo GGUF local"
    backend: BackendKind = "llama_cpp"
    endpoint: str = "http://127.0.0.1:8080"
    model: str = "criba-local"
    gguf_path: str = ""
    server_path: str = ""
    auto_start: bool = True
    reasoning: ReasoningLevel = "balanced"
    context_size: int = 8192
    # -1 delegates GPU offload sizing to current llama.cpp (its default is auto).
    gpu_layers: int = -1
    temperature: float = 0.45
    max_output_tokens: int = 2400

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ModelProfile:
        """Load a profile defensively, ignoring unknown future fields."""

        defaults = cls()
        backend = raw.get("backend")
        reasoning = raw.get("reasoning")
        identifier = _text(raw.get("id"), "", limit=120) or str(uuid.uuid4())
        return cls(
            id=identifier,
            name=_text(raw.get("name"), defaults.name, limit=120),
            backend=backend if backend in {"llama_cpp", "ollama"} else "llama_cpp",
            endpoint=_text(raw.get("endpoint"), defaults.endpoint, limit=2048),
            model=_text(raw.get("model"), defaults.model, limit=240),
            gguf_path=_text(raw.get("gguf_path"), "", limit=32_767),
            server_path=_text(raw.get("server_path"), "", limit=32_767),
            auto_start=(
                raw["auto_start"]
                if isinstance(raw.get("auto_start"), bool)
                else defaults.auto_start
            ),
            reasoning=(
                reasoning if reasoning in {"fast", "balanced", "deep"} else "balanced"
            ),
            context_size=_bounded_int(
                raw.get("context_size"), defaults.context_size, 2048, 131072
            ),
            gpu_layers=_bounded_int(
                raw.get("gpu_layers"), defaults.gpu_layers, -1, 999
            ),
            temperature=_bounded_float(
                raw.get("temperature"), defaults.temperature, 0.0, 1.5
            ),
            max_output_tokens=_bounded_int(
                raw.get("max_output_tokens"),
                defaults.max_output_tokens,
                256,
                16384,
            ),
        )


@dataclass
class ModelSettings:
    """Collection of profiles plus the currently active generation choice."""

    schema_version: int = 1
    enabled: bool = False
    active_profile_id: str = ""
    profiles: list[ModelProfile] = field(default_factory=list)

    def active_profile(self) -> ModelProfile | None:
        """Return the active profile, falling back to the first profile."""

        if not self.profiles:
            return None
        for profile in self.profiles:
            if profile.id == self.active_profile_id:
                return profile
        return self.profiles[0]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the settings without runtime-only state."""

        return {
            "schema_version": self.schema_version,
            "enabled": self.enabled,
            "active_profile_id": self.active_profile_id,
            "profiles": [asdict(profile) for profile in self.profiles],
        }


def default_model_settings() -> ModelSettings:
    """Return a safe disabled configuration with one editable GGUF profile."""

    profile = ModelProfile()
    return ModelSettings(active_profile_id=profile.id, profiles=[profile])


def load_model_settings(path: Path | None = None) -> ModelSettings:
    """Load settings; malformed or missing files degrade to disabled defaults."""

    target = path or model_config_path()
    if not target.is_file():
        return default_model_settings()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise TypeError("La configuración de modelos debe ser un objeto JSON.")
        profiles_raw = raw.get("profiles", [])
        profiles: list[ModelProfile] = []
        seen_ids: set[str] = set()
        for item in profiles_raw:
            if not isinstance(item, dict):
                continue
            profile = ModelProfile.from_dict(item)
            if profile.id in seen_ids:
                profile.id = str(uuid.uuid4())
            seen_ids.add(profile.id)
            profiles.append(profile)
        if not profiles:
            return default_model_settings()
        settings = ModelSettings(
            schema_version=_bounded_int(raw.get("schema_version"), 1, 1, 1),
            enabled=(raw["enabled"] if isinstance(raw.get("enabled"), bool) else False),
            active_profile_id=_text(raw.get("active_profile_id"), "", limit=120),
            profiles=profiles,
        )
        active = settings.active_profile()
        if active is not None:
            settings.active_profile_id = active.id
        return settings
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return default_model_settings()


def save_model_settings(settings: ModelSettings, path: Path | None = None) -> Path:
    """Persist settings atomically and return the destination path."""

    target = path or model_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(
        json.dumps(settings.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temporary, target)
    return target


def active_model_label(settings: ModelSettings | None = None) -> str:
    """Return a concise label suitable for GUI status areas."""

    current = settings or load_model_settings()
    profile = current.active_profile()
    if not current.enabled or profile is None:
        return "Determinista"
    return f"{profile.name} · {profile.reasoning}"
