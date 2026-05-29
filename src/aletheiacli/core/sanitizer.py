"""Zero-Trust Path Sanitizer for secure file system access."""

from __future__ import annotations

import os
import platform
import stat
from pathlib import Path

WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}

INTEGRITY_DENYLIST_NAMES = {
    ".git",
    ".github",
    ".agent",
    ".venv",
    ".cursorrules",
    "pyproject.toml",
    "security.md",
    "changelog.md",
    "license",
}


def verify_no_symlinks_in_ancestors(target_path: Path, root_path: Path) -> None:
    """Recursively verify that no ancestor directory of target_path (up to root_path) is a symlink.

    Also checks for Windows junction points.
    """
    resolved_root = root_path.resolve()
    curr = target_path.parent

    while curr != resolved_root and curr != curr.parent:
        try:
            stat_result = curr.lstat()
            # 1. Check for POSIX / standard symbolic link
            if stat.S_ISLNK(stat_result.st_mode):
                raise ValueError(f"Access denied: symlink detected in parent directory: {curr}")

            # 2. Check for Windows reparse points / junction points
            if platform.system() == "Windows" and (
                getattr(stat_result, "st_file_attributes", 0) & 0x400
            ):
                raise ValueError(
                    f"Access denied: junction or reparse point detected in parent directory: {curr}"
                )
        except FileNotFoundError as exc:
            raise ValueError(f"Access denied: parent directory does not exist: {curr}") from exc

        curr = curr.parent


def sanitize_and_resolve_path(
    user_path: Path, allowed_roots: list[Path], *, write_mode: bool = False
) -> Path:
    """Validate and resolve a user-supplied relative path against allowlisted root paths.

    Args:
        user_path: The untrusted Path provided by the user.
        allowed_roots: The list of validated absolute allowed root directories.
        write_mode: If True, enforces write-specific integrity and symlink checks.

    Returns:
        A resolved, canonical Path that is guaranteed to reside within one of the allowed roots.

    Raises:
        ValueError: If path validation fails (e.g. absolute paths, reserved names, traversal).
        FileNotFoundError: If the target file does not exist (when write_mode is False).
    """
    # 1. Block absolute paths, drives, and anchors (including platform-cross detection)
    path_str = str(user_path).strip()
    if (
        user_path.is_absolute()
        or user_path.drive
        or user_path.anchor
        or (len(path_str) >= 2 and path_str[0].isalpha() and path_str[1] == ":")
        or path_str.startswith("\\\\")
        or path_str.startswith("\\")
        or path_str.startswith("/")
    ):
        raise ValueError("Absolute paths or drive anchors are not allowed")

    # 2. Block Windows Reserved Device Names
    if platform.system() == "Windows":
        for part in user_path.parts:
            p_upper = part.upper()
            stem_upper = Path(part).stem.upper()
            if p_upper in WINDOWS_RESERVED_NAMES or stem_upper in WINDOWS_RESERVED_NAMES:
                raise ValueError("Access to Windows reserved device names is prohibited")

    validated_path: Path | None = None
    matching_root: Path | None = None

    # 3. Resolve and verify boundaries against each allowed root
    for root in allowed_roots:
        try:
            resolved_root = root.resolve(strict=True)
            combined = resolved_root / user_path

            if write_mode:
                # Verify that no ancestor in the requested path is a symlink or junction point
                norm_combined = Path(os.path.normpath(combined))
                curr = norm_combined.parent
                while curr != resolved_root and curr != curr.parent:
                    try:
                        stat_result = curr.lstat()
                        if stat.S_ISLNK(stat_result.st_mode):
                            raise ValueError(
                                f"Access denied: symlink detected in parent directory: {curr}"
                            )
                        if platform.system() == "Windows" and (
                            getattr(stat_result, "st_file_attributes", 0) & 0x400
                        ):
                            raise ValueError(
                                "Access denied: junction or reparse point detected "
                                f"in parent directory: {curr}"
                            )
                    except FileNotFoundError as exc:
                        raise ValueError(
                            f"Access denied: parent directory does not exist: {curr}"
                        ) from exc
                    curr = curr.parent

                # Directory Existence Rule: Parent directory must exist structurally under root
                resolved_parent_loose = combined.parent.resolve(strict=False)
                if resolved_parent_loose.is_relative_to(resolved_root):
                    try:
                        resolved_parent = combined.parent.resolve(strict=True)
                    except FileNotFoundError as exc:
                        raise ValueError(
                            f"Access denied: parent directory does not exist: {combined.parent}"
                        ) from exc
                    resolved_combined = resolved_parent / combined.name
                else:
                    resolved_combined = resolved_parent_loose / combined.name
            else:
                resolved_combined = combined.resolve(strict=True)

            # Native pathlib path-aware boundary check
            if resolved_combined.is_relative_to(resolved_root):
                validated_path = resolved_combined
                matching_root = resolved_root
                break
        except FileNotFoundError:
            continue
        except ValueError:
            # Propagate ValueError from nested exceptions like parent directory missing
            raise

    if validated_path is None or matching_root is None:
        # Check if the combined path exists under any root but was rejected
        for root in allowed_roots:
            try:
                resolved_root = root.resolve(strict=True)
                combined = resolved_root / user_path
                resolved_combined = combined.resolve(strict=False)
                if not resolved_combined.is_relative_to(resolved_root):
                    raise ValueError("Access denied: path traversal or symlink escape detected")
            except Exception:  # noqa: S110
                pass
        raise FileNotFoundError(f"Log file not found or access denied: {user_path}")

    # 4. Strict Normalization Order:
    # Perform integrity checks AFTER resolving to absolute canonical path
    for part in validated_path.parts:
        if part.lower() in INTEGRITY_DENYLIST_NAMES:
            raise ValueError(
                f"Access denied: write or modification of system files is prohibited: {part}"
            )

    # 5. Write-specific Hardening Controls
    if write_mode:
        # Prohibit symlinks on the target file itself if it already exists
        try:
            stat_result = validated_path.lstat()
            if stat.S_ISLNK(stat_result.st_mode):
                raise ValueError("Access denied: writing to symlinks is prohibited")
            if platform.system() == "Windows" and (
                getattr(stat_result, "st_file_attributes", 0) & 0x400
            ):
                raise ValueError("Access denied: writing to junction points is prohibited")
        except FileNotFoundError:
            pass

        # Parent Directory Verification
        verify_no_symlinks_in_ancestors(validated_path, matching_root)

    # 6. Enforce that the target must be a file (not a directory or special device) if it exists
    if validated_path.exists() and not validated_path.is_file():
        raise ValueError("Target path is not a file")

    return validated_path
