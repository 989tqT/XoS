# XoS (eXact Output System)

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
