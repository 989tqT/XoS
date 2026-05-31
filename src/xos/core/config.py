"""Environment-backed configuration (no CLI imports)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

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


def _parse_allowed_roots(raw: str) -> list[Path]:
    stripped = raw.strip()
    if not stripped:
        return []
    roots: list[Path] = []
    for part in stripped.split(os.pathsep):
        part = part.strip()
        if part:
            roots.append(Path(part).resolve())
    return roots


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    max_stdin_bytes: int
    allowed_roots: list[Path]


def load_settings() -> Settings:
    """Load settings from ``XOS_*`` environment variables."""
    max_stdin = _parse_positive_int(
        os.environ.get("XOS_MAX_STDIN_BYTES", ""),
        name="XOS_MAX_STDIN_BYTES",
        default=_DEFAULT_MAX_STDIN_BYTES,
    )
    roots = _parse_allowed_roots(os.environ.get("XOS_ALLOWED_ROOTS", ""))
    return Settings(max_stdin_bytes=max_stdin, allowed_roots=roots)
