"""Unit tests for read-only command execution."""

from __future__ import annotations

import pytest

from aletheiacli import __version__
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


def test_execute_read_log_not_implemented() -> None:
    request = ReadLogRequest.model_validate({"op": "read_log", "path": "/var/log/example.log"})
    with pytest.raises(ExecutionError) as exc_info:
        execute(request)
    assert exc_info.value.code == "NOT_IMPLEMENTED"
