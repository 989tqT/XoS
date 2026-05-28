# AletheiaCLI Documentation

Structured documentation for architecture, development, security, and the agent API.

| Section | Purpose |
|---------|---------|
| [architecture/](architecture/README.md) | System design, layers, JSON I/O contract |
| [development/](development/README.md) | Local setup, testing, CI/CD |
| [security/](security/README.md) | Zero-Trust boundaries, threat model, reporting |
| [api/](api/README.md) | CLI commands and request/response schemas |

## Project status

| Phase | State |
|-------|--------|
| 1.0 Toolchain & src-layout | Done |
| 1.1 Pydantic models | Done |
| 1.2 stdin JSON ingress | Done |
| 1.3 `health` E2E | Done |
| 1.4 `read_log` E2E | Planned |

## Conventions

- Source layout: `src/aletheiacli/` (`commands` → `models` → `core`).
- Agent stdout: single JSON envelope per invocation.
- Changelog: root [CHANGELOG.md](../CHANGELOG.md).
