# CRIBA CURRENT ENGINE

Local, deterministic and explainable pre-response engine. It prepares a `MANDATORY_MODEL_PACKET` with observable assumptions, counterexamples, falsifiable experiments, guardrails and a provisional decision; it never requests or stores private chain-of-thought.

Run on Windows:

```powershell
.\scripts\criba.ps1 activate --query "How can we design secure approvals for agents?"
.\scripts\criba.ps1 serve  # loopback API, Swagger at /docs
.\scripts\criba.ps1 gui
```

The API is loopback only. MCP is available over stdio with `activate_current`, `list_currents`, `explain_selection`, `run_criba`, `build_model_prompt`, `record_decision`, and `compare_runs`. See the Spanish README for setup, security and packaging details.

