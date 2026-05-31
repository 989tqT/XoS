"""Load and validate agent JSON requests from stdin or a debug file."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Final, assert_never

from pydantic import TypeAdapter, ValidationError

from xos.models import (
    AgentRequest,
    CleanupRequest,
    HandshakeRequest,
    HealthRequest,
    ReadLogRequest,
    WriteFileRequest,
)

_REQUEST_ADAPTER: Final[TypeAdapter[AgentRequest]] = TypeAdapter(AgentRequest)


class IngressError(Exception):
    """Base class for request ingress failures."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class PayloadTooLargeError(IngressError):
    """Raised when stdin or file payload exceeds the configured byte limit."""

    def __init__(self, limit: int, actual: int) -> None:
        super().__init__(
            "PAYLOAD_TOO_LARGE",
            f"request payload exceeds limit of {limit} bytes (got {actual})",
        )


class EmptyPayloadError(IngressError):
    """Raised when no JSON body is available."""

    def __init__(self) -> None:
        super().__init__(
            "EMPTY_PAYLOAD", "request body is empty; pipe JSON on stdin or use --request-json"
        )


class InvalidJsonError(IngressError):
    """Raised when the body is not valid JSON."""

    def __init__(self, detail: str) -> None:
        super().__init__("INVALID_JSON", detail)


def read_bytes_limited(source: object, *, max_bytes: int) -> bytes:
    """Read up to ``max_bytes`` from a binary-readable ``source``."""
    chunks: list[bytes] = []
    total = 0
    read = getattr(source, "read", None)
    if read is None:
        msg = "source must support binary read"
        raise TypeError(msg)
    while total < max_bytes:
        chunk = read(min(65_536, max_bytes - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
    if read(1):
        raise PayloadTooLargeError(max_bytes, total + 1)
    return b"".join(chunks)


def load_request_bytes(
    *,
    max_bytes: int,
    request_json: Path | None = None,
) -> bytes:
    """Load raw request bytes from ``--request-json`` file or stdin."""
    if request_json is not None:
        resolved = request_json.expanduser().resolve()
        if not resolved.is_file():
            raise IngressError("REQUEST_FILE_NOT_FOUND", f"request file not found: {resolved}")
        data = resolved.read_bytes()
        if len(data) > max_bytes:
            raise PayloadTooLargeError(max_bytes, len(data))
        if not data.strip():
            raise EmptyPayloadError()
        return data

    if sys.stdin.isatty():
        raise EmptyPayloadError()

    payload = read_bytes_limited(sys.stdin.buffer, max_bytes=max_bytes)
    if not payload.strip():
        raise EmptyPayloadError()
    return payload


def parse_agent_request(payload: bytes) -> AgentRequest:
    """Parse and validate a JSON payload into a discriminated ``AgentRequest``."""
    try:
        document = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise InvalidJsonError(str(exc)) from exc

    if not isinstance(document, dict):
        raise InvalidJsonError("request JSON must be an object")

    try:
        return _REQUEST_ADAPTER.validate_python(document)
    except ValidationError as exc:
        raise IngressError("VALIDATION_ERROR", str(exc)) from exc


def command_name(request: AgentRequest) -> str:
    """Return the CLI command string for a validated request."""
    if isinstance(request, HealthRequest):
        return "health"
    if isinstance(request, HandshakeRequest):
        return "handshake"
    if isinstance(request, CleanupRequest):
        return "cleanup"
    if isinstance(request, ReadLogRequest):
        return "read_log"
    if isinstance(request, WriteFileRequest):
        return "write_file"
    assert_never(request)
