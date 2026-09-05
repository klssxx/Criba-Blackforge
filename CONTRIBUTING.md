# Contributing to CRIBA

Thanks for helping make CRIBA a better engine. The project values determinism,
auditability and zero-friction adoption — keep those three in mind on every change.

## Getting started

```bash
git clone https://github.com/klssxx/Criba-Blackforge.git
cd Criba-Blackforge
uv sync --all-extras --locked
uv run pytest -q
```

> Requires [uv](https://docs.astral.sh/uv/). Python 3.10+.

## Golden rules

1. **Never break determinism.** New randomness must come from an explicit, seeded RNG,
   never from unseeded globals or wall-clock keys. If your feature changes selection
   order for an existing seed, say so clearly in the PR.
2. **Core stays offline and free.** The deterministic engine does not require network
   or credentials. Optional cloud expansion is behind environment variables and degrades
   to the offline fallback — never block core output on the network.
3. **Every idea remains auditable.** Persist what the engine selected and why, so users
   can `explain` their sessions later.
4. **CI is the authority.** The suite (940+ tests) runs on GitHub Actions for every PR;
   mypy strict and ruff run on engine code.

## Development workflow

```bash
uv run pytest -q            # full suite
uv run pytest -q tests/unit # focused iteration
uv run mypy src/criba       # strict type-check the engine
uv run ruff check src       # lint
```

Add tests alongside behaviour changes. For new adapters or pipelines, prefer
dependency-injected, off-network tests (the IIE transport injects a fake sender).

## Releases

- Releases are cut from tags like `v0.2.0` (see `.github/workflows/release.yml`).
- You do not need to publish anything: CI validates the tag, runs the suite, builds
  the portable Windows artifact, attests it (SLSA) and uploads the SBOM.
- User-facing changes are tracked in `CHANGELOG.md` under `[Unreleased]`.

## Questions?

Open a [discussion](https://github.com/klssxx/Criba-Blackforge/discussions) rather
than an issue for "how do I..." questions. Bugs go in issues with the reproduction
template filled in.