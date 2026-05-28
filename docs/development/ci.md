# CI/CD

GitHub Actions run on **push** and **pull_request** to `main` / `master`.

## Workflows

| Workflow | File | Purpose |
|----------|------|---------|
| Test and Lint | `.github/workflows/test-and-lint.yml` | `ruff`, `mypy --strict`, `pytest` + coverage |
| Threat Scan | `.github/workflows/threat-scan.yml` | `bandit` (SAST), `pip-audit` (CVEs) |

### Matrix

- **OS:** `ubuntu-latest`, `windows-latest`
- **Python:** `3.12`
- **Env:** `PYTHONUTF8=1` (Windows UTF-8 stdout for JSON tests)

### Phase 1.3 push checklist

The `feat(cli): wire invoke to executor` commit must include **all** of the following or CI will fail:

- `src/aletheiacli/core/executor.py`
- `src/aletheiacli/commands/invoke.py`
- `tests/unit/test_executor.py`
- `tests/integration/test_invoke_cli.py` (expects `data.status`, not `execution: pending`)

### Schedule

`threat-scan` also runs weekly (Monday 06:00 UTC) for dependency drift.

## Dependabot

`.github/dependabot.yml` — weekly updates for pip and GitHub Actions.

## Local parity

CI commands match the [getting started](getting-started.md) quality gate. Scanners only in CI unless installed locally:

```bash
pip install bandit[toml] pip-audit
bandit -r src -c pyproject.toml -ll
pip-audit
```
