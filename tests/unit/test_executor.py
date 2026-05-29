"""Unit tests for read-only command execution."""

from __future__ import annotations

from pathlib import Path

import pytest

from aletheiacli import __version__
from aletheiacli.core.config import Settings
from aletheiacli.core.executor import ExecutionError, execute, execute_health
from aletheiacli.models import HealthRequest, ReadLogRequest


def test_execute_health_returns_runtime_metadata() -> None:
    data = execute_health(HealthRequest())
    assert data["status"] == "ok"
    assert isinstance(data["platform"], str)
    assert data["cli_version"] == __version__
    assert isinstance(data["python_version"], str)


def test_execute_health_via_dispatcher() -> None:
    data = execute(HealthRequest())
    assert data["status"] == "ok"


def test_execute_read_log_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "logs"
    root.mkdir()
    log_file = root / "app.log"
    log_file.write_text("Hello admin@example.com! password=123\x1b[31mRedText\x00")

    monkeypatch.setattr(
        "aletheiacli.core.executor.load_settings",
        lambda: Settings(max_stdin_bytes=1000, allowed_roots=[root]),
    )

    request = ReadLogRequest.model_validate(
        {
            "op": "read_log",
            "path": "app.log",
            "max_bytes": 100,
        }
    )
    result = execute(request)

    assert result["path"] == "app.log"
    assert result["bytes_read"] == len("Hello admin@example.com! password=123\x1b[31mRedText\x00")
    assert result["truncated"] is False
    content = str(result["content"])
    assert "[MASKED_EMAIL]" in content
    assert "[MASKED_CREDENTIAL]" in content
    # Check that ANSI codes and null bytes are purged
    assert "RedText" in content
    assert "\x1b[31m" not in content
    assert "\x00" not in content


def test_execute_read_log_truncation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "logs"
    root.mkdir()
    log_file = root / "large.log"
    # Write exactly 10 lines of 10 characters as raw bytes (avoiding Windows CRLF conversion)
    log_file.write_bytes(b"123456789\n" * 10)

    monkeypatch.setattr(
        "aletheiacli.core.executor.load_settings",
        lambda: Settings(max_stdin_bytes=1000, allowed_roots=[root]),
    )

    # Ask for strictly 25 bytes
    request = ReadLogRequest.model_validate(
        {
            "op": "read_log",
            "path": "large.log",
            "max_bytes": 25,
        }
    )
    result = execute(request)

    assert result["bytes_read"] == 25
    assert result["truncated"] is True
    assert result["total_file_size"] == 100


def test_execute_read_log_file_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "logs"
    root.mkdir()

    monkeypatch.setattr(
        "aletheiacli.core.executor.load_settings",
        lambda: Settings(max_stdin_bytes=1000, allowed_roots=[root]),
    )

    request = ReadLogRequest.model_validate(
        {
            "op": "read_log",
            "path": "missing.log",
        }
    )
    with pytest.raises(ExecutionError) as exc_info:
        execute(request)
    assert exc_info.value.code == "FILE_NOT_FOUND"


def test_execute_read_log_access_denied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "logs"
    root.mkdir()

    monkeypatch.setattr(
        "aletheiacli.core.executor.load_settings",
        lambda: Settings(max_stdin_bytes=1000, allowed_roots=[root]),
    )

    request = ReadLogRequest.model_validate(
        {
            "op": "read_log",
            "path": "../outside.log",
        }
    )
    with pytest.raises(ExecutionError) as exc_info:
        execute(request)
    assert exc_info.value.code in ("ACCESS_DENIED", "FILE_NOT_FOUND")
