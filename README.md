# CRIBA

**The reproducible ideation engine.** Deterministic, auditable, local-first: the same seed always produces the same ideas — no paid APIs required to get useful output.

CRIBA is a self-contained engine for combinatorial exploration, causal analysis and defensive cybersecurity ideation. It couples an immutable, versioned catalog of innovation and security methods with a repeatable, seed-based selector, a SQLite audit trail for every idea, and (optional) free-tier LLM expansion via Z.ai GLM and Nous `:free` models.

> Read this in [Español](./README.es.md).

---

## Why CRIBA?

Most "AI ideation" tools are black boxes: prompt in, text out, no way to know why or to reproduce the same answer twice.

- **Deterministic by default** — `--seed 42` yields byte-identical results on any machine.
- **Every idea is audited** — SQLite trail per activation: methods used, scores, order, and the exact catalog version.
- **Zero-friction local** — no API key, no network, no telemetry to run the core engine.
- **Free cloud expansion** — optional interpretation of ideas with `GLM-5.3-flash` (Z.ai) and `poolside/laguna-s-2.1:free` (Nous Research), with a deterministic fallback when the network is unavailable.
- **Integrated method catalog** — 130+ innovation/security techniques (TRIZ, Design Thinking, JTBD, FMEA, MITRE ATT&CK, OWASP, STRIDE, Kill Chain…), frozen in JSON with a versioned schema.
- **Provably tried** — 940+ passing tests and the release pipeline builds a signed portable Windows bundle with SLSA provenance.

## Features

| Capability | Description |
|---|---|
| `criba run` / `activate` | Deterministic method selection for a query, with reproducible scoring and session persistence. |
| `criba lottery` | Double-lottery ideation (associative + pure randomness) with explicit seed. |
| `criba blackforge` | Defensive-cybersecurity pipeline: threat analysis, causal reasoning, proposals and S0–S3 security gates. |
| `criba hybrid` | Ensemble → chain → adversarial full pipeline, with optional semantics enhancement. |
| `criba explain` / `compare` | Inspect why a session produced a result; diff two sessions. |
| `criba serve` | Loopback-only JSON API (Swagger at `/docs`). |
| `criba mcp` | MCP server over stdio: `activate_current`, `list_currents`, `explain_selection`, `build_model_prompt`, `record_decision`, `compare_runs`. |
| `criba gui` / `blackforge-gui` | Native PySide6 desktop for CRIBA and BLACKFORGE. |
| Modelos IA dialog | Register local GGUF (llama.cpp) / Ollama profiles; option to expand ideas with free cloud models. |

## Installation

### From PyPI

```bash
pip install criba
```

or run without installing:

```bash
uvx --from criba criba --help
```

> The optional desktop and model features pull extra dependencies:
> `pip install "criba[gui,api,mcp]"`

### From source

```bash
git clone https://github.com/klssxx/Criba-Blackforge.git
cd Criba-Blackforge
uv sync --all-extras --locked
uv run criba --help
```

> On Windows you can also launch the included portable prebuilt (see
> [Releases](https://github.com/klssxx/Criba-Blackforge/releases)).

## 60-second demo

```bash
criba lottery --query "how can we design secure approvals for autonomous agents?" --seed 42 --rounds 3 --batch-size 5
```

Run it twice. The same seed, the same rounds and batch produce the **same ideas**
— that is the reproducibility contract everything else builds on.

Deterministic single activation:

```bash
criba run --query "reduce cold-store energy in data centers" --current auto --mode balanced --json
```

Dashboard / workbench on Windows:

```powershell
scripts\launch_workbench.bat
```

## Reproducibility guarantee

- Catalog files are frozen and versioned (`CURRENT_CATALOG_VERSION`, `SELECTOR_VERSION`).
- The selector is seeded and the ordering is canonical; the output is stable across runs and machines.
- Every activation writes an auditable record in the SQLite store (`artifacts/criba.sqlite3` by default).

## Free cloud expansion (optional, 0€)

When you configure a local GGUF/Ollama profile *or* set the free cloud routes, CRIBA
keeps its deterministic core and uses the model only to draft coherent ideas:

- **Z.ai** — `glm-5.3-flash` at `https://api.z.ai/v1`
- **Nous Research** — `poolside/laguna-s-2.1:free` at `https://api.nousresearch.com/v1` (env `NOUS_API_KEY`)

If the model is unavailable, CRIBA degrades to its offline deterministic fallback —
the output never blocks on the network. Cloud keys are read from environment
variables only and are never stored in the repository.

## Expansion intelligence (IIE)

The engine ships free, key-less prior-art adapters — OpenAlex, Crossref,
EPO patents, NSF grants, GitHub, Wikipedia — designed to connect generated ideas
to the evidence that supports or disproves them, carefully guarded by budget and
rate-limit controls (no network in CI runs).

## Development

```bash
uv run pytest -q            # 940+ tests
uv run mypy src/criba       # strict typing over the engine
uv run ruff check src       # lint
```

Contributions are welcome — see [CONTRIBUTING](./CONTRIBUTING.md) and the
[security policy](./SECURITY.md). Releases are built from tags and published
automatically with SLSA provenance and an SBOM.

## License

Apache License 2.0. See [LICENSE](./LICENSE) and [THIRD_PARTY_NOTICES](./THIRD_PARTY_NOTICES.md).