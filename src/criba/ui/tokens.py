"""Design tokens loaded from data/theme_criba.json (single source of truth).

Contract: docs/STYLE_GUIDE_CRIBA.md — "Si divergen, manda el JSON."
Nothing in the UI may hardcode a color/radius/spacing outside these tokens.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..constants import DATA_ROOT

THEME_PATH = DATA_ROOT / "theme_criba.json"


@dataclass(frozen=True)
class Typography:
    size_px: int
    weight: int


@dataclass(frozen=True)
class Tokens:
    """Flat, attribute-friendly view over theme_criba.json."""

    raw: dict[str, Any]

    # --- colors -----------------------------------------------------------
    @property
    def bg_app(self) -> str: return str(self.raw["color"]["bg"]["app"])
    @property
    def bg_panel(self) -> str: return str(self.raw["color"]["bg"]["panel"])
    @property
    def bg_card(self) -> str: return str(self.raw["color"]["bg"]["card"])
    @property
    def bg_card_hover(self) -> str: return str(self.raw["color"]["bg"]["card_hover"])
    @property
    def bg_inset(self) -> str: return str(self.raw["color"]["bg"]["inset"])
    @property
    def bg_hero(self) -> str:
        # blackforge usa su propio theme_blackforge.json; el criba.json no lo
        # tiene, así que con fallback seguro al bg_app.
        return str(self.raw["color"]["bg"].get("hero", self.raw["color"]["bg"]["app"]))
    @property
    def border_soft(self) -> str: return str(self.raw["color"]["border"]["soft"])
    @property
    def border_active(self) -> str: return str(self.raw["color"]["border"]["active"])
    @property
    def text_primary(self) -> str: return str(self.raw["color"]["text"]["primary"])
    @property
    def text_secondary(self) -> str: return str(self.raw["color"]["text"]["secondary"])
    @property
    def text_muted(self) -> str: return str(self.raw["color"]["text"]["muted"])
    @property
    def accent_blue(self) -> str: return str(self.raw["color"]["accent"]["blue"])
    @property
    def accent_cyan(self) -> str: return str(self.raw["color"]["accent"]["cyan"])
    @property
    def accent_violet(self) -> str: return str(self.raw["color"]["accent"]["violet"])
    @property
    def accent_orange(self) -> str:
        # blackforge usa naranja (theme_blackforge.json); el criba.json no lo
        # tiene siempre. Fallback al primer color del gradiente blackforge.
        try:
            return str(self.raw["gradient"]["blackforge"][0])
        except (KeyError, TypeError):
            return str(self.raw["color"]["accent"].get("orange", "#FF7A1A"))
    @property
    def success(self) -> str: return str(self.raw["color"]["success"])
    @property
    def warning(self) -> str: return str(self.raw["color"]["warning"])
    @property
    def error(self) -> str: return str(self.raw["color"]["error"])

    def chart(self, n: int) -> str:
        return str(self.raw["color"]["chart"][str(n)])

    def gradient(self, name: str) -> tuple[str, str]:
        pair = self.raw["gradient"][name]
        return str(pair[0]), str(pair[1])

    # --- geometry ----------------------------------------------------------
    def radius(self, name: str) -> int:
        return int(self.raw["radius"][name])

    def spacing(self, step: int) -> int:
        return int(self.raw["spacing"][str(step)])

    def icon_size(self, name: str) -> int:
        return int(self.raw["icon"]["size"][name])

    def layout(self, name: str) -> int:
        return int(self.raw["layout"][name])

    # --- typography ---------------------------------------------------------
    @property
    def font_family(self) -> str:
        return str(self.raw["typography"]["family"])

    def type_scale(self, name: str) -> Typography:
        t = self.raw["typography"][name]
        return Typography(size_px=int(t["size_px"]), weight=int(t["weight"]))

    # --- shadow / glow -------------------------------------------------------
    def glow(self, level: int) -> tuple[int, str]:
        g = self.raw["shadow"][f"glow_{level}"]
        return int(g["blur"]), str(g["color"])


@lru_cache(maxsize=1)
def load_tokens(path: Path | None = None) -> Tokens:
    data = json.loads((path or THEME_PATH).read_text(encoding="utf-8"))
    return Tokens(raw=data)
