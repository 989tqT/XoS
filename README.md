# AletheiaCLI

Secure JSON-mediated CLI boundary for AI agents. All agent I/O uses structured JSON on stdin/stdout.

**Current behavior:** `invoke` validates JSON and returns an envelope. Command execution (`health`, `read_log`) is not wired yet — see [docs/api/README.md](docs/api/README.md).

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
mypy
pytest
```

## Invoke (agent)

```bash
echo '{"op":"health"}' | aletheia invoke
# human debug:
aletheia invoke --request-json ./request.json
aletheia invoke --pretty
```

## Layout

```text
src/aletheiacli/
  commands/   invoke
  models/     Pydantic request/response
  core/       config, ingress, emit
tests/unit/ | tests/integration/
docs/       architecture, development, security, api
```

## Documentation

- [docs/](docs/README.md) — architecture, development, security, API
- [SECURITY.md](SECURITY.md) — vulnerability reporting
- [CHANGELOG.md](CHANGELOG.md) — release history

## CI

On push/PR: **Test and Lint** (ruff, mypy strict, pytest on Ubuntu + Windows) and **Threat Scan** (bandit, pip-audit). See [docs/development/ci.md](docs/development/ci.md).

## License

MIT — see [LICENSE](LICENSE).
