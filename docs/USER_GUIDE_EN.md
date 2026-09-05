# User Guide — CRIBA + BLACKFORGE (English)

## What is it?
A deterministic structural-innovation engine. It takes a query, applies
breakup operators over 5 causal axes, generates ideas, scores them with
`value_score = evidence * novelty / cost`, and emits a decision packet.
BLACKFORGE is a specialization over an immutable 723-record catalog with a
safety gate (S0–S3).

## Basic usage (portable GUI)
Double-click `CRIBA-Blackforge.exe` to open the desktop app:
1. Type your query in the bottom box.
2. Click **▶ EJECUTAR CRIBA** (or pick a mode in the *Balanced* dropdown).
3. Check the right panel: *Activation summary*, *Key metrics* and
   *Recommended decision*.
4. **Copiar para el modelo** copies the prompt for your LLM; **Ver paquete
   completo (JSON)** shows the full result; history is saved automatically.

The database is stored at `%LOCALAPPDATA%\CRIBA-Blackforge\criba.sqlite3`.

## Advanced usage (CLI, optional)
When running from source, prepare the environment with `uv sync --all-extras --locked` and use `uv run criba`:
```text
uv sync --all-extras --locked
uv run --locked criba list-currents
uv run --locked criba activate --query "your innovation question"
uv run --locked criba activate --file samples\query_example.txt
uv run --locked criba --database my.sqlite3 explain --session <activation_id>
```

## Flows
- **New idea**: `activate` generates 12 ideas by default.
- **Generate**: implicit in `activate` (divergence + cross-consistency).
- **Evaluate**: packet includes `value_score`, `pipeline_action`, `recommended_status`.
- **Save**: `activate` persists to SQLite (via `--database`).
- **History**: `explain --session <id>`, `compare --session-a A --session-b B`.
- **Blackforge**: runs internally as a library (213 tests verify it).

## Best practices
- Use `--database` to avoid touching the default DB (`artifacts/criba.sqlite3`).
- To automate, capture `activation_id` from the output JSON.

## Requirements
Windows 10/11 x64, 16 GB RAM (CPU only). No installation required.
