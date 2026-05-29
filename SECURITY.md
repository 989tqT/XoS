# Security Policy

## Supported versions

| Version        | Supported |
| -------------- | --------- |
| `0.0.x` pre-alpha | Best-effort (development) |
| `0.1.x` alpha/beta | Planned |
| `1.0.x`          | Planned after RC |

## Reporting a vulnerability

**Do not** open a public GitHub issue for security-sensitive reports.

1. Email or contact the repository maintainer privately (add your channel here).
2. Include steps to reproduce, impact assessment, and affected version/commit.
3. Allow reasonable time for a fix before public disclosure.

## Security posture (current)

- JSON-only agent I/O with Pydantic validation (`extra="forbid"`).
- No `shell=True` in executor; read-only file access is governed by strict directory-traversal and symlink controls (Phase 1.4).
- Double-layer masking (global multiline + line-by-line single line) and XML CDATA breakout defense to prevent Second-Order Prompt Injection (Phase 1.4).
- CI: `ruff`, `mypy --strict`, `pytest`, `bandit`, `pip-audit` on push/PR.

See [docs/security/](docs/security/README.md) for trust boundaries and known risks.
