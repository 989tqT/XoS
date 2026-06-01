# XoS (eXact Output System)

[![CI/CD Status](https://img.shields.io/github/actions/workflow/status/989tqT/XoS/test-and-lint.yml?branch=main)](https://github.com/989tqT/XoS/blob/main/.github/workflows/test-and-lint.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/TQT/XoS/blob/main/LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.12+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-E92063?style=flat&logo=pydantic&logoColor=white)](https://pydantic.dev/)
[![Tested with Pytest](https://img.shields.io/badge/tested_with-pytest-0A9EDC?style=flat&logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Lint: Ruff](https://img.shields.io/badge/lint-ruff-000000?style=flat&logo=ruff&logoColor=white)](https://github.com/astral-sh/ruff)
[![Types: Mypy Strict](https://img.shields.io/badge/types-Mypy%20Strict-2F5C8F?style=flat&logo=python&logoColor=white)](https://mypy-lang.org/)
[![Security: Bandit](https://img.shields.io/badge/security-Bandit-success?style=flat&logo=securityscorecard&logoColor=white)](https://github.com/PyCQA/bandit)


XoS is a secure JSON-mediated CLI boundary for AI agents. All agent I/O uses structured JSON on stdin/stdout.

**Current behavior:** `health`, `handshake`, `cleanup`, `read_log`, and `write_file` run end-to-end via `invoke`. Inputs are strictly sanitized, outputs are masked under Zero-Trust protocols, state is managed in a concurrent-safe SQLite database, and active session scratchpads are dynamically allowlisted for isolated work — see [docs/README.md](docs/README.md).

## Requirements

- Python **3.12+**

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS
pip install -e ".[dev]"
ruff check src tests
ruff format --check src tests
mypy src
pytest
```

## Invoke (agent)

### Probe health
```bash
echo '{"op":"health"}' | xos invoke
```

### Session Lifecycle & Ephemeral Scratchpads (Phase 1.6)

1. **Establish Session Lease (Handshake)**:
   ```bash
   echo '{"op":"handshake"}' | xos invoke
   ```
   *Returns a secure UUID `session_id` and the physical path to your dynamic scratchpad directory (e.g. `<appDataDir>/sessions/<session_id>/scratchpad/`).*

2. **Secure Write targeted at Scratchpad**:
   ```bash
   echo '{"op":"write_file", "path":"temp.txt", "content":"hello from session!", "session_id":"<session_id>"}' | xos invoke
   ```

3. **Read back content within Scratchpad**:
   ```bash
   echo '{"op":"read_log", "path":"temp.txt", "session_id":"<session_id>"}' | xos invoke
   ```

4. **Exclusively purge session assets (Cleanup)**:
   ```bash
   echo '{"op":"cleanup", "session_id":"<session_id>"}' | xos invoke
   ```

## Layout

```text
src/xos/
  commands/   invoke CLI interface
  models/     Pydantic discriminated request/response schemas
  core/       config, ingress, emit, sanitizer, executor, state
tests/
  unit/       unit test suites
  integration/ integration/E2E test pipelines
docs/         architecture, development, security, API specifications
```

## Documentation

- [docs/](docs/README.md) — architecture, development, security, API
- [SECURITY.md](SECURITY.md) — vulnerability reporting policy
- [CHANGELOG.md](CHANGELOG.md) — release history

## CI

On push/PR: **Test and Lint** (ruff, mypy strict, pytest on Ubuntu + Windows) and **Threat Scan** (bandit, pip-audit). See [docs/development/ci.md](docs/development/ci.md).

## License

MIT — see [LICENSE](LICENSE).
