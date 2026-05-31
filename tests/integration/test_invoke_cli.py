"""Integration tests for ``xos invoke``."""

from __future__ import annotations

import json
import platform
from pathlib import Path

import pytest  # noqa: TC002
from typer.testing import CliRunner

from xos import __version__
from xos.__main__ import app

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
    monkeypatch.setenv("XOS_ALLOWED_ROOTS", str(tmp_path))

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
    monkeypatch.setenv("XOS_ALLOWED_ROOTS", str(tmp_path))

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


def test_invoke_session_e2e_lifecycle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Point the session db and App Data root to a temporary folder
    monkeypatch.setenv("XOS_APP_DATA_DIR", str(tmp_path))

    # 1. Run handshake
    result = runner.invoke(app, ["invoke"], input='{"op": "handshake"}')
    assert result.exit_code == 0, result.stdout
    response = json.loads(result.stdout)
    assert response["ok"] is True
    session_id = response["data"]["session_id"]
    scratchpad_str = response["data"]["scratchpad"]

    # 2. Write file inside the scratchpad
    write_payload = {
        "op": "write_file",
        "path": "test_e2e.txt",
        "content": "E2E scratchpad writing is flawless!",
        "session_id": session_id,
    }
    result_write = runner.invoke(app, ["invoke"], input=json.dumps(write_payload))
    assert result_write.exit_code == 0, result_write.stdout
    response_write = json.loads(result_write.stdout)
    assert response_write["ok"] is True

    # 3. Read file back from scratchpad
    read_payload = {
        "op": "read_log",
        "path": "test_e2e.txt",
        "session_id": session_id,
    }
    result_read = runner.invoke(app, ["invoke"], input=json.dumps(read_payload))
    assert result_read.exit_code == 0, result_read.stdout
    response_read = json.loads(result_read.stdout)
    assert response_read["ok"] is True
    assert "flawless" in response_read["data"]["content"]

    # 4. Clean up session
    cleanup_payload = {
        "op": "cleanup",
        "session_id": session_id,
    }
    result_cleanup = runner.invoke(app, ["invoke"], input=json.dumps(cleanup_payload))
    assert result_cleanup.exit_code == 0, result_cleanup.stdout
    response_cleanup = json.loads(result_cleanup.stdout)
    assert response_cleanup["ok"] is True
    assert response_cleanup["data"]["status"] == "cleaned"

    # 5. Verify physically deleted
    assert not Path(scratchpad_str).exists()

