# Security policy

CRIBA is a local-first tool: by default it makes no network requests and stores its
state on your own machine. When you enable the optional cloud expansion, credentials
are read from environment variables only and are never written to project files.

## Supported versions

Security fixes are published for the latest release and, where feasible, the
previous release.

## Reporting a vulnerability

If you believe you found a security issue — including leaked credentials in any
public artifact, unsafe defaults in the local API, or unintended network behaviour —
please report it privately so it stays out of public issue threads:

1. Open a [private vulnerability report](https://github.com/klssxx/Criba-Blackforge/security/advisories/new)
   on this repository, or
2. Open a normal issue marked `security` if you prefer a lighter path.

Include the affected version, a minimal reproduction, and your expected vs observed
behaviour. We will confirm receipt and aim to respond within one week.

## Scope

- The deterministic engine and its SQLite audit trail (confidentiality of session data).
- The loopback API (`criba serve`) and MCP server (should never bind a non-loopback
  interface unless the user explicitly opts in).
- The optional cloud adapters (credentials handling, rate-limit safety).
- The release pipeline (portable artifact integrity, SLSA attestation, SBOM).