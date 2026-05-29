# Architecture Overview

AletheiaCLI is a **mediation layer** between untrusted AI agents and the host OS. Agents never pass raw shell strings; they send validated JSON and receive a masked JSON envelope.

## Layers

```text
┌─────────────────────────────────────────────────────────┐
│  AI Agent (untrusted)                                    │
└───────────────────────────┬─────────────────────────────┘
                            │ stdin JSON / optional --request-json
                            ▼
┌─────────────────────────────────────────────────────────┐
│  commands/   Typer CLI — parse ingress, emit stdout      │
└───────────────────────────┬─────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────┐
│  models/     Pydantic — validate requests & responses    │
└───────────────────────────┬─────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────┐
│  core/       sanitizer → executor (read/write limits)   │
└───────────────────────────┬─────────────────────────────┘
                            ▼
                     OS / filesystem (subset)
```

## Trust boundaries

| Zone | Trust level |
|------|-------------|
| Agent input | **Untrusted** — prompt injection, malicious paths |
| AletheiaCLI process | **Semi-trusted** — runs as invoking user |
| Allowlisted paths | **Constrained** — enforced in `core` (Phase 1.4+) |

## Design rules

- **Allowlist over denylist** for operations and paths.
- **Integrity Denylists** on resolved canonical paths to prevent agent self-modification.
- **No `shell=True`** for subprocess (when used).
- **Cross-platform paths** via `pathlib.Path` only.
