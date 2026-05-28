"""Smoke tests for Phase 1.0 bootstrap."""

from __future__ import annotations

import aletheiacli
from aletheiacli.__main__ import app


def test_version_is_semver_like() -> None:
    assert aletheiacli.__version__ == "0.0.1"


def test_typer_app_exists() -> None:
    assert app.info.name == "aletheia"
