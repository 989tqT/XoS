# Changelog

All notable changes to **AletheiaCLI** are documented here.

## [Unreleased]

### Added
- **executor**: `health` command — cross-platform runtime metadata via `platform`/`sys` (no shell)
- **cli**: `aletheia invoke` — stdin JSON ingress, `--request-json` debug path, `--pretty`; envelope stdout; exit code 0/1
- **core**: `config`, `ingress`, `emit` — payload size limit (`ALETHEIA_MAX_STDIN_BYTES`), structured ingress errors
- **ci**: GitHub Actions `test-and-lint` (ruff, mypy, pytest; Ubuntu + Windows) and `threat-scan` (bandit, pip-audit on runtime deps); Dependabot for pip and Actions
- **ci**: pin `pytest>=9.0.3` (CVE-2025-71176); upgrade pip in workflows before audit
- **docs**: `docs/` tree (architecture, development, security, api), root `SECURITY.md`
- **models**: Pydantic agent envelope (`ok`, `data`, `meta`, `errors`) with `meta.trace_id`; `HealthRequest`, `ReadLogRequest`, discriminated `AgentRequest`

### Security & Zero-Trust
- **sanitizer**: Native `pathlib`-based directory-traversal and symlink escape mitigation with Windows Reserved Device Names prevention (Phase 1.4)
- **masking**: Dual-layer PII/credential masking and XML CDATA injection shield against Second-Order Prompt Injection (Phase 1.4)
- **executor**: Low-RAM line-by-line reading pipeline and XML-safe control character purifier (Phase 1.4)

### Changed
- **cli**: Fully operational `read_log` dispatcher E2E logic (Phase 1.4)
- **ci**: split pip install steps for Windows; set `PYTHONUTF8` and Node 24 action env
- **cli**: `invoke` dispatches validated requests through `core.executor` (replaces ingress-only stub)
- **docs**: document `health` response fields and `NOT_IMPLEMENTED` for `read_log`

### Planned
- Phase 1.5 - 2.0: Extended sandbox execution boundaries, write-operation TOCTOU mitigation, and network egress mediation rules.
