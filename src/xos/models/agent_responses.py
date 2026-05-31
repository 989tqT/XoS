"""JSON response envelope for agent-facing stdout."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ErrorItem(BaseModel):
    """Structured error returned in the envelope when ``ok`` is false."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    code: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=4096)


class ResponseMeta(BaseModel):
    """Correlation and command metadata for tracing and auditing."""

    model_config = ConfigDict(extra="forbid")

    trace_id: UUID
    command: str = Field(min_length=1, max_length=128)
    dry_run: bool = False
    version: str = Field(min_length=1, max_length=32)


class AgentResponse(BaseModel):
    """Canonical JSON envelope written to stdout for AI agents."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    data: dict[str, Any] = Field(default_factory=dict)
    meta: ResponseMeta
    errors: list[ErrorItem] = Field(default_factory=list)
