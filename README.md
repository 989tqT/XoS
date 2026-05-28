# AletheiaCLI

Secure JSON-mediated CLI boundary for AI agents. All agent I/O uses structured JSON on stdin/stdout.

## Status

**Pre-alpha** (`v0.0.x`) — Phase 1.0 toolchain bootstrap.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e ".[dev]"
ruff check src tests
ruff format --check src tests
mypy
pytest
```

## License

MIT
