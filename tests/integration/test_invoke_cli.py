"""Integration tests for ``aletheia invoke``."""

from __future__ import annotations

import json
import platform
from pathlib import Path

import pytest  # noqa: TC002
from typer.testing import CliRunner

from aletheiacli import __version__
from aletheiacli.__main__ import app

runner = CliRunner()


def test_invoke_health_stdin() -> None:
    result = runner.invoke(app, ["invoke"], input='{"op": "health"}')
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["meta"]["command"] == "health"
    assert "trace_id" in payload["meta"]
    assert payload["data"]["status"] == "ok"
    assert payload["data"]["platform"] == platform.system()
    assert payload["data"]["cli_version"] == __version__


def test_invoke_read_log_access_denied() -> None:
    result = runner.invoke(
        app,
        ["invoke"],
        input='{"op": "read_log", "path": "/var/log/example.log"}',
    )
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["errors"][0]["code"] == "ACCESS_DENIED"


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
    assert payload["data"]["status"] == "ok"


def test_invoke_pretty_stdout() -> None:
    result = runner.invoke(app, ["invoke", "--pretty"], input='{"op": "health"}')
    assert result.exit_code == 0
    assert "\n" in result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True


def test_invoke_write_file_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Set allowed roots to the temp directory
    monkeypatch.setenv("ALETHEIA_ALLOWED_ROOTS", str(tmp_path))

    payload = {
        "op": "write_file",
        "path": "test_write.txt",
        "content": "E2E Integration Write works!",
    }

    result = runner.invoke(
        app,
        ["invoke"],
        input=json.dumps(payload),
    )
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["ok"] is True
    assert response["data"]["bytes_written"] == len("E2E Integration Write works!")

    written_file = tmp_path / "test_write.txt"
    assert written_file.exists()
    assert written_file.read_text(encoding="utf-8") == "E2E Integration Write works!"


def test_invoke_write_file_denylist_denied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALETHEIA_ALLOWED_ROOTS", str(tmp_path))

    payload = {
        "op": "write_file",
        "path": ".cursorrules",
        "content": "AI OVERRIDE RULE",
    }

    result = runner.invoke(
        app,
        ["invoke"],
        input=json.dumps(payload),
    )
    assert result.exit_code == 1
    response = json.loads(result.stdout)
    assert response["ok"] is False
    assert response["errors"][0]["code"] == "ACCESS_DENIED"
