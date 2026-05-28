"""Integration tests for ``aletheia invoke`` (Phase 1.2)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from aletheiacli.__main__ import app

runner = CliRunner()


def test_invoke_health_stdin() -> None:
    result = runner.invoke(app, ["invoke"], input='{"op": "health"}')
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["meta"]["command"] == "health"
    assert "trace_id" in payload["meta"]
    assert payload["data"]["op"] == "health"
    assert payload["data"]["execution"] == "pending"


def test_invoke_validation_error() -> None:
    result = runner.invoke(app, ["invoke"], input='{"op": "rm_rf"}')
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["errors"][0]["code"] == "VALIDATION_ERROR"


def test_invoke_empty_stdin() -> None:
    result = runner.invoke(app, ["invoke"])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["errors"][0]["code"] == "EMPTY_PAYLOAD"


def test_invoke_request_json_file(tmp_path: Path) -> None:
    req = tmp_path / "health.json"
    req.write_text('{"op": "health"}', encoding="utf-8")
    result = runner.invoke(app, ["invoke", "--request-json", str(req)])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True


def test_invoke_pretty_stdout() -> None:
    result = runner.invoke(app, ["invoke", "--pretty"], input='{"op": "health"}')
    assert result.exit_code == 0
    assert "\n" in result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
