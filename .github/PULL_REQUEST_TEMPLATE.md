## Summary

<!-- What does this change do, in one or two sentences? -->

## Reproducibility

- [ ] The change keeps results stable for the same seed (no new unseeded randomness).
- [ ] No network/credentials introduced in core paths (or explicitly optional and documented).
- [ ] New behaviour has test coverage; the full suite passes (`uv run pytest -q`).

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Packaging / CI / release
- [ ] Refactor (no behaviour change)

## Checklist

- [ ] `uv run pytest -q` passes
- [ ] `uv run mypy src/criba` passes (if engine code touched)
- [ ] `uv run ruff check src` passes
- [ ] CHANGELOG updated under `[Unreleased]` when user-facing