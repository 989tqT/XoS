"""Unit tests for JSON ingress (Phase 1.2)."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from aletheiacli.core.config import load_settings
from aletheiacli.core.ingress import (
    InvalidJsonError,
    PayloadTooLargeError,
    load_request_bytes,
    parse_agent_request,
)


def test_parse_health_request() -> None:
    req = parse_agent_request(b'{"op": "health"}')
    assert req.op == "health"


def test_parse_rejects_non_object_json() -> None:
    with pytest.raises(InvalidJsonError):
        parse_agent_request(b"[]")


def test_load_request_bytes_from_file(tmp_path: Path) -> None:
    path = tmp_path / "req.json"
    path.write_text('{"op": "health"}', encoding="utf-8")
    raw = load_request_bytes(max_bytes=4096, request_json=path)
    assert json.loads(raw)["op"] == "health"


def test_load_request_bytes_rejects_oversized_file(tmp_path: Path) -> None:
    path = tmp_path / "big.json"
    path.write_bytes(b"x" * 32)
    with pytest.raises(PayloadTooLargeError):
        load_request_bytes(max_bytes=16, request_json=path)


def test_read_bytes_limited_enforces_cap() -> None:
    from aletheiacli.core.ingress import read_bytes_limited

    source = io.BytesIO(b"a" * 100)
    with pytest.raises(PayloadTooLargeError):
        read_bytes_limited(source, max_bytes=10)


def test_settings_default_max_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ALETHEIA_MAX_STDIN_BYTES", raising=False)
    assert load_settings().max_stdin_bytes == 1_048_576
