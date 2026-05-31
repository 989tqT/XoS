"""Unit tests for the Zero-Trust Path Sanitizer."""

from __future__ import annotations

import platform
from pathlib import Path

import pytest

from xos.core.sanitizer import sanitize_and_resolve_path


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


def test_sanitize_write_mode_non_existent_file_allowed(tmp_path: Path) -> None:
    root = tmp_path / "logs"
    root.mkdir()
    allowed = [root]
    # In write_mode=True, a non-existent file is allowed if the parent dir exists
    resolved = sanitize_and_resolve_path(Path("new.log"), allowed, write_mode=True)
    assert resolved == (root / "new.log").resolve()


def test_sanitize_write_mode_parent_dir_must_exist(tmp_path: Path) -> None:
    root = tmp_path / "logs"
    root.mkdir()
    allowed = [root]
    # Directory Existence Rule: sub/ doesn't exist, must be rejected
    with pytest.raises(ValueError, match="parent directory does not exist"):
        sanitize_and_resolve_path(Path("sub/new.log"), allowed, write_mode=True)


def test_sanitize_write_mode_integrity_denylist(tmp_path: Path) -> None:
    root = tmp_path / "logs"
    root.mkdir()
    allowed = [root]

    # Block writing to .cursorrules
    with pytest.raises(ValueError, match="write or modification of system files is prohibited"):
        sanitize_and_resolve_path(Path(".cursorrules"), allowed, write_mode=True)

    # Obfuscated relative paths must be resolved first and blocked
    with pytest.raises(ValueError, match="write or modification of system files is prohibited"):
        sanitize_and_resolve_path(Path("sub/../.cursorrules"), allowed, write_mode=True)


def test_sanitize_write_mode_rejects_symlink_file(tmp_path: Path) -> None:
    root = tmp_path / "logs"
    root.mkdir()
    allowed = [root]

    target = root / "target.log"
    target.write_text("real data")

    symlink_file = root / "link.log"
    try:
        symlink_file.symlink_to(target)
    except OSError:
        pytest.skip("Symlinks not supported or requires admin on Windows")

    with pytest.raises(ValueError, match="writing to symlinks is prohibited"):
        sanitize_and_resolve_path(Path("link.log"), allowed, write_mode=True)


def test_sanitize_write_mode_rejects_symlink_parent(tmp_path: Path) -> None:
    root = tmp_path / "logs"
    root.mkdir()
    allowed = [root]

    real_sub = tmp_path / "real_sub"
    real_sub.mkdir()

    symlink_dir = root / "sub_link"
    try:
        symlink_dir.symlink_to(real_sub)
    except OSError:
        pytest.skip("Symlinks not supported or requires admin on Windows")

    # Accessing file inside symlink parent must be rejected by Parent Directory Verification
    with pytest.raises(ValueError, match="symlink detected in parent directory"):
        sanitize_and_resolve_path(Path("sub_link/app.log"), allowed, write_mode=True)
