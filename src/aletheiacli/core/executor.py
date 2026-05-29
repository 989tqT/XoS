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

from aletheiacli import __version__
from aletheiacli.core.config import load_settings
from aletheiacli.core.masking import secure_envelope_cdata
from aletheiacli.core.sanitizer import sanitize_and_resolve_path
from aletheiacli.models import (
    AgentRequest,
    HealthRequest,
    ReadLogRequest,
    WriteFileRequest,
)

INVALID_XML_CHARS_RE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]|(?:\x1B\[[0-9;]*[mK])"
)

# Quotas for security defenses
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

    # 1. Path Sanitization & Resolution
    try:
        resolved_path = sanitize_and_resolve_path(request.path, settings.allowed_roots)
    except FileNotFoundError as exc:
        raise ExecutionError("FILE_NOT_FOUND", str(exc)) from exc
    except ValueError as exc:
        raise ExecutionError("ACCESS_DENIED", str(exc)) from exc

    # 2. Line-by-line safe file reading (Zero-Trust Memory Exhaustion & Circuit Breaker)
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

    # 3. Safe Decode (Replace errors) & XML Character Purging
    raw_content = b"".join(lines)
    decoded_string = raw_content.decode("utf-8", errors="replace")
    sanitized_string = INVALID_XML_CHARS_RE.sub("", decoded_string)

    # 4. Prompt Injection & PII Masking + XML CDATA Wrapping
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

    # 1. Path Sanitization & Resolution in write_mode
    try:
        resolved_path = sanitize_and_resolve_path(
            request.path, settings.allowed_roots, write_mode=True
        )
    except FileNotFoundError as exc:
        raise ExecutionError("FILE_NOT_FOUND", str(exc)) from exc
    except ValueError as exc:
        raise ExecutionError("ACCESS_DENIED", str(exc)) from exc

    # 2. Disk Space Guard (shutil.disk_usage)
    try:
        usage = shutil.disk_usage(resolved_path.parent)
        if usage.free < MIN_DISK_FREE_SPACE_BYTES:
            raise ExecutionError(
                "DISK_EXHAUSTION", "Insufficient free disk space on target partition"
            )
    except Exception as exc:
        if isinstance(exc, ExecutionError):
            raise

    # 3. Log Directory Folder Size Quota Guard (50MB Cap)
    target_root: Path | None = None
    for root in settings.allowed_roots:
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

    # 4. Windows-Specific Reparse/Junction Point Guard on target file
    if platform.system() == "Windows":
        try:
            stat_result = resolved_path.lstat()
            if getattr(stat_result, "st_file_attributes", 0) & 0x400:
                raise ExecutionError(
                    "ACCESS_DENIED", "Writing to NTFS junction or reparse point is prohibited"
                )
        except FileNotFoundError:
            pass

    # 5. Secure O_NOFOLLOW file descriptor write
    raw_content = request.content.encode("utf-8", errors="replace")

    flags = os.O_CREAT | os.O_WRONLY | os.O_TRUNC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    fd = None
    try:
        fd = os.open(resolved_path, flags, mode=0o644)
        with open(fd, "wb") as f:  # noqa: PTH123
            f.write(raw_content)
        fd = None  # Closed by the context manager
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


def execute(request: AgentRequest) -> dict[str, object]:
    """Dispatch a validated request to the appropriate handler."""
    if isinstance(request, HealthRequest):
        return execute_health(request)
    if isinstance(request, ReadLogRequest):
        return execute_read_log(request)
    if isinstance(request, WriteFileRequest):
        return execute_write_file(request)
    assert_never(request)
