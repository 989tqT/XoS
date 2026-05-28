"""Unit tests for Phase 1.1 Pydantic contracts."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import TypeAdapter, ValidationError

from aletheiacli.models import (
    AgentRequest,
    AgentResponse,
    ErrorItem,
    HealthRequest,
    ReadLogRequest,
    ResponseMeta,
)


class TestHealthRequest:
    def test_defaults_op(self) -> None:
        req = HealthRequest()
        assert req.op == "health"

    def test_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValidationError):
            HealthRequest.model_validate({"op": "health", "evil": True})


class TestReadLogRequest:
    def test_parses_string_path(self) -> None:
        req = ReadLogRequest.model_validate(
            {"op": "read_log", "path": "/var/log/syslog", "max_bytes": 1024}
        )
        assert req.path == Path("/var/log/syslog")
        assert req.max_bytes == 1024

    def test_max_bytes_bounds(self) -> None:
        with pytest.raises(ValidationError):
            ReadLogRequest.model_validate(
                {"op": "read_log", "path": "/var/log/example.log", "max_bytes": 0}
            )
        with pytest.raises(ValidationError):
            ReadLogRequest.model_validate(
                {"op": "read_log", "path": "/var/log/example.log", "max_bytes": 2_000_000}
            )

    def test_rejects_null_byte_in_path(self) -> None:
        with pytest.raises(ValidationError):
            ReadLogRequest.model_validate({"op": "read_log", "path": "/var/log/ex\x00ample.log"})


class TestAgentRequestDiscriminator:
    def test_health_variant(self) -> None:
        adapter: TypeAdapter[AgentRequest] = TypeAdapter(AgentRequest)
        req = adapter.validate_python({"op": "health"})
        assert isinstance(req, HealthRequest)

    def test_read_log_variant(self) -> None:
        adapter: TypeAdapter[AgentRequest] = TypeAdapter(AgentRequest)
        req = adapter.validate_python({"op": "read_log", "path": "logs/app.log"})
        assert isinstance(req, ReadLogRequest)

    def test_unknown_op_fails(self) -> None:
        adapter: TypeAdapter[AgentRequest] = TypeAdapter(AgentRequest)
        with pytest.raises(ValidationError):
            adapter.validate_python({"op": "rm_rf"})


class TestAgentResponseEnvelope:
    def test_round_trip_json(self) -> None:
        trace = UUID("550e8400-e29b-41d4-a716-446655440000")
        envelope = AgentResponse(
            ok=True,
            data={"status": "ok"},
            meta=ResponseMeta(
                trace_id=trace,
                command="health",
                dry_run=False,
                version="0.0.1",
            ),
            errors=[],
        )
        raw = envelope.model_dump_json()
        parsed = AgentResponse.model_validate_json(raw)
        assert parsed == envelope
        payload = json.loads(raw)
        assert payload["meta"]["trace_id"] == str(trace)
        assert payload["ok"] is True

    def test_error_item_in_envelope(self) -> None:
        envelope = AgentResponse(
            ok=False,
            data={},
            meta=ResponseMeta(
                trace_id=UUID(int=0),
                command="read_log",
                version="0.0.1",
            ),
            errors=[ErrorItem(code="PATH_DENIED", message="path outside allowlist")],
        )
        assert envelope.errors[0].code == "PATH_DENIED"
        assert envelope.ok is False

    def test_rejects_extra_top_level_fields(self) -> None:
        with pytest.raises(ValidationError):
            AgentResponse.model_validate(
                {
                    "ok": True,
                    "data": {},
                    "meta": {
                        "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                        "command": "health",
                        "version": "0.0.1",
                    },
                    "errors": [],
                    "injected": True,
                }
            )
