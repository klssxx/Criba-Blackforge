"""CRIBA 60-second demo: reproducible ideation.

Same seed, same catalog, same ideas — on any machine, with no network and no
API key. This is the contract everything else builds on.

Run:
    uv run python examples/getting_started.py
or:
    python examples/getting_started.py
"""
from __future__ import annotations

from criba.catalog import methods
from criba.lottery import LotteryEngine

QUERY = "how can we design secure approvals for autonomous agents?"


def run_once(seed: int = 42) -> list[dict]:
    """Two alternating lottery rounds over the frozen catalog, seeded."""
    engine = LotteryEngine.from_methods(methods(), seed=seed)
    engine.run_round(mode="alternating", batch_size=8, query=QUERY)
    engine.run_round(mode="alternating", batch_size=8, query=QUERY)
    return engine.get_top_ideas(5)


def main() -> int:
    first = run_once(seed=42)
    second = run_once(seed=42)

    print("CRIBA — reproducible ideation demo")
    print("=" * 60)
    for i, idea in enumerate(first, 1):
        print(f"{i:2d}. [{idea['quality']:13}] score {idea['score']:.3f}  {idea['title'][:66]}")

    first_signature = [(idea["title"], idea["score"]) for idea in first]
    second_signature = [(idea["title"], idea["score"]) for idea in second]
    if first_signature != second_signature:
        print("[FAIL] outputs differ for the same seed — reproducibility broken!")
        return 1
    print("[ok] Two engines, same seed, same ideas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())