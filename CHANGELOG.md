# Changelog

All notable changes to **AletheiaCLI** are documented here.

## [Unreleased]

### Added
- **cli**: `aletheia invoke` — stdin JSON ingress, `--request-json` debug path, `--pretty`; envelope stdout; exit code 0/1
- **core**: `config`, `ingress`, `emit` — payload size limit (`ALETHEIA_MAX_STDIN_BYTES`), structured ingress errors
- **ci**: GitHub Actions `test-and-lint` (ruff, mypy, pytest; Ubuntu + Windows) and `threat-scan` (bandit, pip-audit on runtime deps); Dependabot for pip and Actions
- **ci**: pin `pytest>=9.0.3` (CVE-2025-71176); upgrade pip in workflows before audit
- **docs**: `docs/` tree (architecture, development, security, api), root `SECURITY.md`
- **models**: Pydantic agent envelope (`ok`, `data`, `meta`, `errors`) with `meta.trace_id`; `HealthRequest`, `ReadLogRequest`, discriminated `AgentRequest`

### Changed
- **docs**: synchronized README and `docs/` with Phase 1.2 runtime; clarified interim `execution: pending` payload
- **cli**: replace phase-specific stub note in invoke success `data` with `execution: pending`

### Planned
- Phase 1.3–1.4: `health` / `read_log` E2E with sanitizer, executor, mask
