"""Unit tests for the Zero-Trust Path Sanitizer."""

from __future__ import annotations

import platform
from pathlib import Path

import pytest

from aletheiacli.core.sanitizer import sanitize_and_resolve_path


def test_sanitize_rejects_absolute_paths() -> None:
    allowed = [Path("/var/log/allowed")]
    # Test Unix absolute path
    with pytest.raises(ValueError, match="Absolute paths or drive anchors"):
        sanitize_and_resolve_path(Path("/etc/passwd"), allowed)
    # Test Windows absolute paths or drives
    with pytest.raises(ValueError, match="Absolute paths or drive anchors"):
        sanitize_and_resolve_path(Path("C:\\Windows\\system32"), allowed)


@pytest.mark.skipif(
    platform.system() != "Windows",
    reason="Windows reserved names only applicable on Windows",
)
def test_sanitize_rejects_windows_reserved_device_names() -> None:
    allowed = [Path("C:\\logs")]
    with pytest.raises(ValueError, match="Windows reserved device names"):
        sanitize_and_resolve_path(Path("CON"), allowed)
    with pytest.raises(ValueError, match="Windows reserved device names"):
        sanitize_and_resolve_path(Path("sub/dir/aux.log"), allowed)


def test_sanitize_valid_path_under_root(tmp_path: Path) -> None:
    # Set up safe test environment
    root = tmp_path / "logs"
    root.mkdir()
    log_file = root / "app.log"
    log_file.write_text("secure log content")

    allowed = [root]
    resolved = sanitize_and_resolve_path(Path("app.log"), allowed)
    assert resolved == log_file.resolve()


def test_sanitize_rejects_traversal_attempts(tmp_path: Path) -> None:
    root = tmp_path / "logs"
    root.mkdir()
    secret_dir = tmp_path / "secrets"
    secret_dir.mkdir()
    secret_file = secret_dir / "passwords.txt"
    secret_file.write_text("supersecret")

    allowed = [root]
    # Test typical relative directory traversal
    with pytest.raises(FileNotFoundError):
        sanitize_and_resolve_path(Path("../secrets/passwords.txt"), allowed)


def test_sanitize_rejects_non_existent_files(tmp_path: Path) -> None:
    root = tmp_path / "logs"
    root.mkdir()
    allowed = [root]
    with pytest.raises(FileNotFoundError):
        sanitize_and_resolve_path(Path("does_not_exist.log"), allowed)


def test_sanitize_rejects_directories_instead_of_files(tmp_path: Path) -> None:
    root = tmp_path / "logs"
    root.mkdir()
    subdir = root / "sub"
    subdir.mkdir()

    allowed = [root]
    with pytest.raises(ValueError, match="Target path is not a file"):
        sanitize_and_resolve_path(Path("sub"), allowed)


def test_sanitize_supports_multiple_roots(tmp_path: Path) -> None:
    root1 = tmp_path / "logs1"
    root1.mkdir()
    root2 = tmp_path / "logs2"
    root2.mkdir()

    log1 = root1 / "app1.log"
    log1.write_text("log1 content")
    log2 = root2 / "app2.log"
    log2.write_text("log2 content")

    allowed = [root1, root2]

    assert sanitize_and_resolve_path(Path("app1.log"), allowed) == log1.resolve()
    assert sanitize_and_resolve_path(Path("app2.log"), allowed) == log2.resolve()
