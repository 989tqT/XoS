"""JSON request schemas accepted from stdin or ``--request-json``."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HealthRequest(BaseModel):
    """Probe CLI availability and runtime metadata."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    op: Literal["health"] = "health"


class HandshakeRequest(BaseModel):
    """Initiate a secure session scratchpad lease."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    op: Literal["handshake"] = "handshake"
    session_id: UUID | None = None
    ttl_seconds: int = Field(default=3600, ge=60, le=86400)


class CleanupRequest(BaseModel):
    """Terminate session scratchpad lease and purge files completely."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    op: Literal["cleanup"] = "cleanup"
    session_id: UUID


class ReadLogRequest(BaseModel):
    """Read a log file under an allowlisted root (path policy enforced in core executor)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    op: Literal["read_log"] = "read_log"
    path: Path
    max_bytes: int = Field(default=65_536, ge=1, le=1_048_576)
    session_id: UUID | None = None

    @field_validator("path", mode="before")
    @classmethod
    def coerce_path(cls, value: object) -> Path:
        if isinstance(value, Path):
            candidate = value
        elif isinstance(value, str):
            candidate = Path(value)
        else:
            msg = "path must be a string or Path"
            raise TypeError(msg)
        if "\x00" in str(candidate):
            msg = "path must not contain null bytes"
            raise ValueError(msg)
        return candidate


class WriteFileRequest(BaseModel):
    """Write content to a file under allowed root (integrity and path checks enforced in core)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    op: Literal["write_file"] = "write_file"
    path: Path
    content: str = Field(max_length=1_048_576)
    session_id: UUID | None = None

    @field_validator("path", mode="before")
    @classmethod
    def coerce_path(cls, value: object) -> Path:
        if isinstance(value, Path):
            candidate = value
        elif isinstance(value, str):
            candidate = Path(value)
        else:
            msg = "path must be a string or Path"
            raise TypeError(msg)
        if "\x00" in str(candidate):
            msg = "path must not contain null bytes"
            raise ValueError(msg)
        return candidate


AgentRequest = Annotated[
    HealthRequest | HandshakeRequest | CleanupRequest | ReadLogRequest | WriteFileRequest,
    Field(discriminator="op"),
]
