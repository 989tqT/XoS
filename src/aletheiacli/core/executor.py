"""Read-only command execution (no CLI imports)."""

from __future__ import annotations

import platform
import re
import sys
from typing import assert_never

from aletheiacli import __version__
from aletheiacli.core.config import load_settings
from aletheiacli.core.masking import secure_envelope_cdata
from aletheiacli.core.sanitizer import sanitize_and_resolve_path
from aletheiacli.models import AgentRequest, HealthRequest, ReadLogRequest

INVALID_XML_CHARS_RE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]|(?:\x1B\[[0-9;]*[mK])"
)


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


def execute_read_log(request: ReadLogRequest) -> dict[str, object]:
    """Execute log reading with strict boundary validation, sanitization, and output masking."""
    settings = load_settings()

    # 1. Path Sanitization & Resolution
    try:
        resolved_path = sanitize_and_resolve_path(request.path, settings.allowed_roots)
    except FileNotFoundError as exc:
        raise ExecutionError("FILE_NOT_FOUND", str(exc)) from exc
    except ValueError as exc:
        raise ExecutionError("ACCESS_DENIED", str(exc)) from exc

    # 2. Line-by-line safe file reading (Zero-Trust Memory Exhaustion & Circuit Breaker)
    total_bytes = 0
    lines: list[bytes] = []
    truncated = False
    max_bytes = request.max_bytes

    try:
        with resolved_path.open("rb") as f:
            for line_bytes in f:
                total_bytes += len(line_bytes)
                if total_bytes > max_bytes:
                    allowed_len = len(line_bytes) - (total_bytes - max_bytes)
                    if allowed_len > 0:
                        lines.append(line_bytes[:allowed_len])
                    truncated = True
                    break
                lines.append(line_bytes)
    except Exception as exc:
        raise ExecutionError("READ_ERROR", f"Failed to read file: {exc}") from exc

    total_file_size = resolved_path.stat().st_size
    bytes_read = sum(len(line) for line in lines)

    # 3. Safe Decode (Replace errors) & XML Character Purging
    raw_content = b"".join(lines)
    decoded_string = raw_content.decode("utf-8", errors="replace")
    sanitized_string = INVALID_XML_CHARS_RE.sub("", decoded_string)

    # 4. Prompt Injection & PII Masking + XML CDATA Wrapping
    secure_content = secure_envelope_cdata(sanitized_string)

    return {
        "path": str(request.path),
        "resolved_path": str(resolved_path),
        "bytes_read": bytes_read,
        "total_file_size": total_file_size,
        "truncated": truncated,
        "content": secure_content,
    }


def execute(request: AgentRequest) -> dict[str, object]:
    """Dispatch a validated request to the appropriate read-only handler."""
    if isinstance(request, HealthRequest):
        return execute_health(request)
    if isinstance(request, ReadLogRequest):
        return execute_read_log(request)
    assert_never(request)

