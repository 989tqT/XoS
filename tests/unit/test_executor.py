"""Unit tests for read-only and write command execution."""

from __future__ import annotations

import collections
import platform
import stat
from pathlib import Path

import pytest

from xos import __version__
from xos.core.config import Settings
from xos.core.executor import ExecutionError, execute, execute_health
from xos.models import HealthRequest, ReadLogRequest, WriteFileRequest


def test_execute_health_returns_runtime_metadata() -> None:
    data = execute_health(HealthRequest())
    assert data["status"] == "ok"
    assert isinstance(data["platform"], str)
    assert data["cli_version"] == __version__
    assert isinstance(data["python_version"], str)


def test_execute_health_via_dispatcher() -> None:
    data = execute(HealthRequest())
    assert data["status"] == "ok"


def test_execute_read_log_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "logs"
    root.mkdir()
    log_file = root / "app.log"
    log_file.write_text("Hello admin@example.com! password=123\x1b[31mRedText\x00")

    monkeypatch.setattr(
        "xos.core.executor.load_settings",
        lambda: Settings(max_stdin_bytes=1000, allowed_roots=[root]),
    )

    request = ReadLogRequest.model_validate(
        {
            "op": "read_log",
            "path": "app.log",
            "max_bytes": 100,
        }
    )
    result = execute(request)

    assert result["path"] == "app.log"
    assert result["bytes_read"] == len("Hello admin@example.com! password=123\x1b[31mRedText\x00")
    assert result["truncated"] is False
    content = str(result["content"])
    assert "[MASKED_EMAIL]" in content
    assert "[MASKED_CREDENTIAL]" in content
    assert "RedText" in content
    assert "\x1b[31m" not in content
    assert "\x00" not in content


def test_execute_read_log_truncation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "logs"
    root.mkdir()
    log_file = root / "large.log"
    # Write exactly 10 lines of 10 characters as raw bytes (avoiding Windows CRLF conversion)
    log_file.write_bytes(b"123456789\n" * 10)

    monkeypatch.setattr(
        "xos.core.executor.load_settings",
        lambda: Settings(max_stdin_bytes=1000, allowed_roots=[root]),
    )

    # Ask for strictly 25 bytes
    request = ReadLogRequest.model_validate(
        {
            "op": "read_log",
            "path": "large.log",
            "max_bytes": 25,
        }
    )
    result = execute(request)

    assert result["bytes_read"] == 25
    assert result["truncated"] is True
    assert result["total_file_size"] == 100


def test_execute_read_log_file_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "logs"
    root.mkdir()

    monkeypatch.setattr(
        "xos.core.executor.load_settings",
        lambda: Settings(max_stdin_bytes=1000, allowed_roots=[root]),
    )

    request = ReadLogRequest.model_validate(
        {
            "op": "read_log",
            "path": "missing.log",
        }
    )
    with pytest.raises(ExecutionError) as exc_info:
        execute(request)
    assert exc_info.value.code == "FILE_NOT_FOUND"


def test_execute_read_log_access_denied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "logs"
    root.mkdir()

    monkeypatch.setattr(
        "xos.core.executor.load_settings",
        lambda: Settings(max_stdin_bytes=1000, allowed_roots=[root]),
    )

    request = ReadLogRequest.model_validate(
        {
            "op": "read_log",
            "path": "../outside.log",
        }
    )
    with pytest.raises(ExecutionError) as exc_info:
        execute(request)
    assert exc_info.value.code in ("ACCESS_DENIED", "FILE_NOT_FOUND")


def test_execute_write_file_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "logs"
    root.mkdir()

    monkeypatch.setattr(
        "xos.core.executor.load_settings",
        lambda: Settings(max_stdin_bytes=1000, allowed_roots=[root]),
    )

    request = WriteFileRequest.model_validate(
        {
            "op": "write_file",
            "path": "new_file.txt",
            "content": "Secret text here!",
        }
    )
    result = execute(request)

    assert result["bytes_written"] == len("Secret text here!")
    assert result["status"] == "success"

    written_file = root / "new_file.txt"
    assert written_file.exists()
    assert written_file.read_text(encoding="utf-8") == "Secret text here!"


def test_execute_write_file_disk_exhaustion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "logs"
    root.mkdir()

    monkeypatch.setattr(
        "xos.core.executor.load_settings",
        lambda: Settings(max_stdin_bytes=1000, allowed_roots=[root]),
    )

    # Mock shutil.disk_usage to trigger disk exhaustion
    usage = collections.namedtuple("usage", ["total", "used", "free"])
    monkeypatch.setattr("shutil.disk_usage", lambda path: usage(1000, 1000, 0))

    request = WriteFileRequest.model_validate(
        {
            "op": "write_file",
            "path": "no_disk.txt",
            "content": "Disk Full!",
        }
    )
    with pytest.raises(ExecutionError) as exc_info:
        execute(request)
    assert exc_info.value.code == "DISK_EXHAUSTION"


def test_execute_write_file_quota_exceeded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "logs"
    root.mkdir()

    # Mock _get_dir_size directly to trigger quota limit (50MB)
    monkeypatch.setattr(
        "xos.core.executor.load_settings",
        lambda: Settings(max_stdin_bytes=1000, allowed_roots=[root]),
    )
    monkeypatch.setattr("xos.core.executor._get_dir_size", lambda path: 50_000_001)

    request = WriteFileRequest.model_validate(
        {
            "op": "write_file",
            "path": "quota_full.txt",
            "content": "Exceeds quota!",
        }
    )
    with pytest.raises(ExecutionError) as exc_info:
        execute(request)
    assert exc_info.value.code == "QUOTA_EXCEEDED"


@pytest.mark.skipif(
    platform.system() != "Windows",
    reason="Junction mock works only on Windows attributes",
)
def test_execute_write_file_junction_point(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "logs"
    root.mkdir()

    monkeypatch.setattr(
        "xos.core.executor.load_settings",
        lambda: Settings(max_stdin_bytes=1000, allowed_roots=[root]),
    )

    # Mock lstat to simulate Windows Junction Attribute (0x400 reparse point)
    orig_lstat = Path.lstat

    class MockStat:
        st_file_attributes = 0x400
        st_mode = stat.S_IFDIR

    # Pre-create the file to allow lstat mock
    fake_junction = root / "junction.txt"
    fake_junction.write_text("dummy")

    def mock_lstat(self: Path) -> object:
        if "junction.txt" in str(self):
            return MockStat()
        return orig_lstat(self)

    monkeypatch.setattr(Path, "lstat", mock_lstat)

    request = WriteFileRequest.model_validate(
        {
            "op": "write_file",
            "path": "junction.txt",
            "content": "Excite junction",
        }
    )
    with pytest.raises(ExecutionError) as exc_info:
        execute(request)
    assert exc_info.value.code == "ACCESS_DENIED"


def test_execute_handshake_and_cleanup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from xos.models import CleanupRequest, HandshakeRequest

    # Mock get_app_data_dir to point to a temporary folder
    monkeypatch.setenv("XOS_APP_DATA_DIR", str(tmp_path))

    req_handshake = HandshakeRequest(ttl_seconds=3600)
    result_handshake = execute(req_handshake)

    assert "session_id" in result_handshake
    assert "scratchpad" in result_handshake
    assert result_handshake["status"] == "active"

    session_id = result_handshake["session_id"]
    scratchpad_path = Path(str(result_handshake["scratchpad"]))
    assert scratchpad_path.exists()

    # Verify write_file works to the scratchpad dynamically
    from xos.models import WriteFileRequest
    req_write = WriteFileRequest(
        op="write_file",
        path="temp.txt",
        content="Dynamic scratchpad content works!",
        session_id=session_id,
    )
    result_write = execute(req_write)
    assert result_write["status"] == "success"

    written_file = scratchpad_path / "temp.txt"
    assert written_file.exists()
    assert written_file.read_text(encoding="utf-8") == "Dynamic scratchpad content works!"

    # Run cleanup
    req_cleanup = CleanupRequest(session_id=session_id)
    result_cleanup = execute(req_cleanup)

    assert result_cleanup["status"] == "cleaned"
    assert not scratchpad_path.exists()


def test_execute_handshake_quota_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from xos.models import HandshakeRequest

    monkeypatch.setenv("XOS_APP_DATA_DIR", str(tmp_path))

    # Mock active session count to simulate 50 active sessions
    monkeypatch.setattr("xos.core.state.get_active_session_count", lambda db: 50)

    req = HandshakeRequest(ttl_seconds=3600)
    with pytest.raises(ExecutionError) as exc_info:
        execute(req)
    assert exc_info.value.code == "QUOTA_EXCEEDED"

