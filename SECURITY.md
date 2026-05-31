# Security Policy

## Supported versions

| Version        | Supported |
| -------------- | --------- |
| `0.0.x` pre-alpha | Best-effort (development) |
| `0.1.x` alpha/beta | Planned |
| `1.0.x`          | Planned after RC |

## Reporting a vulnerability

**Do not** open a public GitHub issue for security-sensitive reports.

1. Email or contact the repository maintainer privately.
2. Include steps to reproduce, impact assessment, and affected version/commit.
3. Allow reasonable time for a fix before public disclosure.

## Security posture (current)

- **Input Ingress boundaries:** JSON-only agent I/O with rigid Pydantic validation (`extra="forbid"`).
- **Execution isolation:** No shell environments spawned (`shell=True` strictly forbidden); file access is strictly normalized and resolved against allowlisted roots (Phase 1.4).
- **Write Hardening:** Securing file modification through recursive parent symlink/junction audits, strict normalization checks, static integrity denylists, minimum disk space guards (100MB), and folder storage quotas (50MB) (Phase 1.5).
- **Session Isolation & Ephemeral Scratchpads (Phase 1.6):**
  - Connects to SQLite backing database utilizing high timeout settings (`30.0s`) and secure WAL configurations to mitigate lock contentions.
  - Automates active session capacities (< 50 concurrent active session quota) to prevent handshake flooding DoS attacks.
  - Dynamically allowlists session-isolated scratchpads, locking permissions using POSIX `0o700` flags.
  - Employs transactional garbage collection (purging DB metadata first inside a transaction to claim ownership) preventing concurrent TOCTOU file deletion races.
- **Output Masking:** Double-layered regex filters (secrets, AWS keys, GitHub tokens, credentials, PII) and XML CDATA wrap-enveloping to prevent downstream second-order prompt injections.
- **CI Pipelines:** Automated Ruff, strict MyPy, bandit, pip-audit, and dual-OS (Ubuntu + Windows) pytest runs.

See [docs/security/](docs/security/README.md) for trust boundaries and detailed threat models.
