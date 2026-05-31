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
mypy src
pytest
```

## Layout (actual)

```text
src/xos/
  __main__.py      Typer app + invoke registration
  commands/
    invoke.py      stdin / --request-json ingress
  models/
    agent_requests.py
    agent_responses.py
  core/
    config.py      XOS_* env loading configurations
    ingress.py     load + validate JSON
    emit.py        envelope stdout
    executor.py    command dispatch (health, handshake, cleanup, read_log, write_file)
    sanitizer.py   zero-trust path boundary validation
    masking.py     sensitive logs masking engine
    state.py       zero-trust session state tracking database
tests/
  unit/
  integration/
```

## Environment

Copy `.env.example` to `.env` (never commit `.env`):

| Variable | Purpose |
|----------|---------|
| `XOS_ALLOWED_ROOTS` | Comma-separated absolute paths for `read_log` and `write_file` (Phase 1.4 / 1.5) |
| `XOS_MAX_STDIN_BYTES` | Max stdin / request file size (default `1048576`) |
| `XOS_APP_DATA_DIR` | Absolute path to secure App Data Directory backing session tracking database and scratchpad workspaces (Phase 1.6) |

## Invoke locally

```bash
echo '{"op":"health"}' | xos invoke
```
