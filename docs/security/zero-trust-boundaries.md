# Zero-Trust Boundaries

## What AletheiaCLI enforces (target state)

| Control | Phase | Mechanism |
|---------|-------|-----------|
| Structured input | 1.1 ✓ | Pydantic, `extra="forbid"` |
| No shell injection | 1.4 / 1.5 ✓ | argv-only / Python I/O, no `shell=True` |
| Path allowlist | 1.4 / 1.5 ✓ | `ALETHEIA_ALLOWED_ROOTS` + strict normalization resolution |
| Output masking | 1.4 ✓ | Regex mask on logs/errors |
| Write protection | 1.5 ✓ | `os.O_NOFOLLOW` + ancestor symlink/junction audits + folder quotas (50MB) + disk space guards (100MB) |
| Dry-run plan | 3 | `--dry-run` structured plan |

## What it does **not** enforce

- **Process privilege:** CLI runs as the invoking user; misconfigured allowlists can expose sensitive files.
- **Network egress:** not restricted by the CLI itself.
- **Agent cognition:** log content may contain prompt-injection text; downstream agents must treat `data` as untrusted.

## Operational guidance

- Run under a **low-privilege** dedicated user.
- Keep `ALETHEIA_ALLOWED_ROOTS` minimal (log directories only).
- Review JSON output before feeding back into models for sensitive deployments.
