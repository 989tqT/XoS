"""Environment-backed configuration (no CLI imports)."""

from __future__ import annotations

import os
from dataclasses import dataclass

_DEFAULT_MAX_STDIN_BYTES = 1_048_576


def _parse_positive_int(raw: str, *, name: str, default: int) -> int:
    stripped = raw.strip()
    if not stripped:
        return default
    value = int(stripped)
    if value < 1:
        msg = f"{name} must be a positive integer"
        raise ValueError(msg)
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    max_stdin_bytes: int


def load_settings() -> Settings:
    """Load settings from ``ALETHEIA_*`` environment variables."""
    max_stdin = _parse_positive_int(
        os.environ.get("ALETHEIA_MAX_STDIN_BYTES", ""),
        name="ALETHEIA_MAX_STDIN_BYTES",
        default=_DEFAULT_MAX_STDIN_BYTES,
    )
    return Settings(max_stdin_bytes=max_stdin)
