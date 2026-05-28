"""Read-only command execution (no CLI imports)."""

from __future__ import annotations

import platform
import sys
from typing import assert_never

from aletheiacli import __version__
from aletheiacli.models import AgentRequest, HealthRequest, ReadLogRequest


class ExecutionError(Exception):
    """Raised when a validated request cannot be executed."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def execute_health(_request: HealthRequest) -> dict[str, object]:
    """Return runtime metadata without invoking a shell."""
    return {
        "status": "ok",
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "executable": sys.executable,
        "cli_version": __version__,
    }


def execute(request: AgentRequest) -> dict[str, object]:
    """Dispatch a validated request to the appropriate read-only handler."""
    if isinstance(request, HealthRequest):
        return execute_health(request)
    if isinstance(request, ReadLogRequest):
        raise ExecutionError(
            "NOT_IMPLEMENTED",
            "read_log execution is not available yet",
        )
    assert_never(request)
