"""Zero-Trust Command Execution Engine (no CLI imports)."""

from __future__ import annotations

import contextlib
import os
import platform
import re
import shutil
import sys
from pathlib import Path
from typing import assert_never

from xos import __version__
from xos.core.config import load_settings
from xos.core.masking import secure_envelope_cdata
from xos.core.sanitizer import sanitize_and_resolve_path
from xos.models import (
    AgentRequest,
    CleanupRequest,
    HandshakeRequest,
    HealthRequest,
    ReadLogRequest,
    WriteFileRequest,
)

INVALID_XML_CHARS_RE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]|(?:\x1B\[[0-9;]*[mK])"
)

# quota for security defense
MAX_ROOT_DIR_SIZE_BYTES = 50_000_000  # 50MB Cap
MIN_DISK_FREE_SPACE_BYTES = 100_000_000  # 100MB Cap


class ExecutionError(Exception):
    """Raised when a validated request cannot be executed."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def _get_dir_size(path: Path) -> int:
    """Recursively calculate the total size of files inside a directory."""
    total = 0
    for entry in os.scandir(path):
        if entry.is_file(follow_symlinks=False):
            with contextlib.suppress(FileNotFoundError):
                total += entry.stat(follow_symlinks=False).st_size
        elif entry.is_dir(follow_symlinks=False):
            total += _get_dir_size(Path(entry.path))
    return total


def execute_health(_request: HealthRequest) -> dict[str, object]:
    """Return runtime metadata without invoking a shell."""
    return {
        "status": "ok",
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "executable": sys.executable,
        "cli_version": __version__,
    }


def execute_read_log(request: ReadLogRequest) -> dict[str, object]:
    """Execute log reading with strict boundary validation, sanitization, and output masking."""
    settings = load_settings()

    # 1. path sanitization & resolution
    try:
        resolved_path = sanitize_and_resolve_path(
            request.path, settings.allowed_roots, session_id=request.session_id
        )
    except FileNotFoundError as exc:
        raise ExecutionError("FILE_NOT_FOUND", str(exc)) from exc
    except ValueError as exc:
        raise ExecutionError("ACCESS_DENIED", str(exc)) from exc

    # 2. line-by-line safe file read (Zero-Trust memory exhaustion & circuit breaker)
    total_bytes = 0
    lines: list[bytes] = []
    truncated = False
    max_bytes = request.max_bytes

    try:
        with resolved_path.open("rb") as f:
            for line_bytes in f:
                total_bytes += len(line_bytes)
                if total_bytes > max_bytes:
                    allowed_len = len(line_bytes) - (total_bytes - max_bytes)
                    if allowed_len > 0:
                        lines.append(line_bytes[:allowed_len])
                    truncated = True
                    break
                lines.append(line_bytes)
    except Exception as exc:
        raise ExecutionError("READ_ERROR", f"Failed to read file: {exc}") from exc

    total_file_size = resolved_path.stat().st_size
    bytes_read = sum(len(line) for line in lines)

    # 3. safe decode (replace error) & XML character purge
    raw_content = b"".join(lines)
    decoded_string = raw_content.decode("utf-8", errors="replace")
    sanitized_string = INVALID_XML_CHARS_RE.sub("", decoded_string)

    # 4. prompt injection & PII masking + XML CDATA wrapping
    secure_content = secure_envelope_cdata(sanitized_string)

    return {
        "path": str(request.path),
        "resolved_path": str(resolved_path),
        "bytes_read": bytes_read,
        "total_file_size": total_file_size,
        "truncated": truncated,
        "content": secure_content,
    }


def execute_write_file(request: WriteFileRequest) -> dict[str, object]:
    """Execute file writing with secure boundary validation, symlink checks, and quotas."""
    settings = load_settings()

    # 1. path sanitization & resolution in write_mode
    try:
        resolved_path = sanitize_and_resolve_path(
            request.path,
            settings.allowed_roots,
            write_mode=True,
            session_id=request.session_id,
        )
    except FileNotFoundError as exc:
        raise ExecutionError("FILE_NOT_FOUND", str(exc)) from exc
    except ValueError as exc:
        raise ExecutionError("ACCESS_DENIED", str(exc)) from exc

    # 2. disk space guard (shutil.disk_usage)
    try:
        usage = shutil.disk_usage(resolved_path.parent)
        if usage.free < MIN_DISK_FREE_SPACE_BYTES:
            raise ExecutionError(
                "DISK_EXHAUSTION", "Insufficient free disk space on target partition"
            )
    except Exception as exc:
        if isinstance(exc, ExecutionError):
            raise

    # 3. log directory folder size quota guard (50MB cap)
    roots_to_check = list(settings.allowed_roots)
    if request.session_id is not None:
        from xos.core.state import get_db_path, verify_session

        try:
            scratchpad_path = verify_session(get_db_path(), request.session_id)
            roots_to_check.append(scratchpad_path)
        except Exception as exc:
            raise ExecutionError("ACCESS_DENIED", f"Invalid or expired session: {exc}") from exc

    target_root: Path | None = None
    for root in roots_to_check:
        try:
            resolved_root = root.resolve(strict=True)
            if resolved_path.is_relative_to(resolved_root):
                target_root = resolved_root
                break
        except Exception:  # noqa: S112
            continue

    if target_root is not None:
        try:
            current_root_size = _get_dir_size(target_root)
            existing_size = resolved_path.stat().st_size if resolved_path.exists() else 0
            new_data_len = len(request.content.encode("utf-8", errors="replace"))
            projected_size = current_root_size - existing_size + new_data_len
            if projected_size > MAX_ROOT_DIR_SIZE_BYTES:
                raise ExecutionError(
                    "QUOTA_EXCEEDED",
                    f"Write exceeds allowed root size quota of {MAX_ROOT_DIR_SIZE_BYTES} bytes",
                )
        except Exception as exc:
            if isinstance(exc, ExecutionError):
                raise

    # 4. windows-specific reparse/junction point guard on target file
    if platform.system() == "Windows":
        try:
            stat_result = resolved_path.lstat()
            if getattr(stat_result, "st_file_attributes", 0) & 0x400:
                raise ExecutionError(
                    "ACCESS_DENIED", "Writing to NTFS junction or reparse point is prohibited"
                )
        except FileNotFoundError:
            pass

    # 5. secure O_NOFOLLOW file descriptor write
    raw_content = request.content.encode("utf-8", errors="replace")

    flags = os.O_CREAT | os.O_WRONLY | os.O_TRUNC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    fd = None
    try:
        fd = os.open(resolved_path, flags, mode=0o644)
        with open(fd, "wb") as f:  # noqa: PTH123
            f.write(raw_content)
        fd = None  # close by context manager
    except FileNotFoundError as exc:
        raise ExecutionError(
            "FILE_NOT_FOUND", f"Target file or parent directory missing: {exc}"
        ) from exc
    except PermissionError as exc:
        raise ExecutionError("ACCESS_DENIED", f"Permission denied during write: {exc}") from exc
    except Exception as exc:
        raise ExecutionError("WRITE_ERROR", f"Failed securely writing to file: {exc}") from exc
    finally:
        if fd is not None:
            with contextlib.suppress(Exception):
                os.close(fd)

    return {
        "path": str(request.path),
        "resolved_path": str(resolved_path),
        "bytes_written": len(raw_content),
        "status": "success",
    }


def execute_handshake(request: HandshakeRequest) -> dict[str, object]:
    """Initiate a secure session scratchpad lease, run lazy GC, and enforce limit."""
    import uuid

    from xos.core.state import (
        get_active_session_count,
        get_app_data_dir,
        get_db_path,
        lazy_garbage_collect,
        register_session,
    )

    db_path = get_db_path()

    # 1. run race-condition-shielded lazy garbage collect to free expired slot
    lazy_garbage_collect(db_path)

    # 2. enforce global cap of 50 active session
    if get_active_session_count(db_path) >= 50:
        raise ExecutionError("QUOTA_EXCEEDED", "Active session quota limit exceeded (50 max)")

    # 3. establish session ID and secure scratchpad folder
    session_id = request.session_id or uuid.uuid4()
    scratchpad_path = get_app_data_dir() / "sessions" / str(session_id) / "scratchpad"

    scratchpad_path.mkdir(parents=True, exist_ok=True)
    if platform.system() != "Windows":
        scratchpad_path.chmod(0o700)

    # 4. register session in database
    try:
        register_session(db_path, session_id, request.ttl_seconds, scratchpad_path)
    except Exception as exc:
        raise ExecutionError("WRITE_ERROR", f"Failed to register session: {exc}") from exc

    return {
        "session_id": str(session_id),
        "scratchpad": str(scratchpad_path),
        "status": "active",
    }


def execute_cleanup(request: CleanupRequest) -> dict[str, object]:
    """Exclusively terminate session lease and delete physical directories securely."""
    from xos.core.state import get_db_path, purge_session

    db_path = get_db_path()
    scratchpad_path = purge_session(db_path, request.session_id)

    if scratchpad_path is not None:
        if scratchpad_path.exists():
            with contextlib.suppress(FileNotFoundError, PermissionError):
                shutil.rmtree(scratchpad_path)
        # suppress error if delete session folder itself fail
        with contextlib.suppress(FileNotFoundError, PermissionError, OSError):
            scratchpad_path.parent.rmdir()

    return {
        "session_id": str(request.session_id),
        "status": "cleaned",
    }


def execute(request: AgentRequest) -> dict[str, object]:
    """Dispatch a validated request to the appropriate handler."""
    if isinstance(request, HealthRequest):
        return execute_health(request)
    if isinstance(request, HandshakeRequest):
        return execute_handshake(request)
    if isinstance(request, CleanupRequest):
        return execute_cleanup(request)
    if isinstance(request, ReadLogRequest):
        return execute_read_log(request)
    if isinstance(request, WriteFileRequest):
        return execute_write_file(request)
    assert_never(request)
