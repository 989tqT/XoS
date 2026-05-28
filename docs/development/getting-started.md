# Getting Started

## Requirements

- Python **3.12+**
- Git (maintainer-operated; see project agent rules)

## Setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Unix
source .venv/bin/activate

pip install -e ".[dev]"
```

## Local quality gate (run before commit)

```bash
ruff check src tests
ruff format --check src tests
mypy
pytest
```

## Layout (actual)

```text
src/aletheiacli/
  __main__.py      Typer app + invoke registration
  commands/
    invoke.py      stdin / --request-json ingress
  models/
    agent_requests.py
    agent_responses.py
  core/
    config.py      ALETHEIA_* env
    ingress.py     load + validate JSON
    emit.py        envelope stdout
    executor.py    read-only command dispatch (health)
tests/
  unit/
  integration/
```

**Not yet present (planned):** `core/sanitizer.py`, `core/logger.py`; `read_log` in executor.

## Environment

Copy `.env.example` to `.env` (never commit `.env`):

| Variable | Purpose |
|----------|---------|
| `ALETHEIA_ALLOWED_ROOTS` | Comma-separated absolute paths for `read_log` (Phase 1.4) |
| `ALETHEIA_MAX_STDIN_BYTES` | Max stdin / request file size (default `1048576`) |

## Invoke locally

```bash
echo '{"op":"health"}' | aletheia invoke
```
