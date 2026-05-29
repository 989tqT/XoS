"""Zero-Trust Path Sanitizer for secure file system access."""

from __future__ import annotations

import platform
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


def sanitize_and_resolve_path(user_path: Path, allowed_roots: list[Path]) -> Path:
    """Validate and resolve a user-supplied relative path against allowlisted root paths.

    Args:
        user_path: The untrusted Path provided by the user.
        allowed_roots: The list of validated absolute allowed root directories.

    Returns:
        A resolved, canonical Path that is guaranteed to reside within one of the allowed roots.

    Raises:
        ValueError: If path validation fails (e.g. absolute paths, reserved names, traversal).
        FileNotFoundError: If the target file does not exist.
    """
    # 1. Block absolute paths, drives, and anchors
    if user_path.is_absolute() or user_path.drive or user_path.anchor:
        raise ValueError("Absolute paths or drive anchors are not allowed")

    # 2. Block Windows Reserved Device Names
    if platform.system() == "Windows":
        for part in user_path.parts:
            p_upper = part.upper()
            stem_upper = Path(part).stem.upper()
            if p_upper in WINDOWS_RESERVED_NAMES or stem_upper in WINDOWS_RESERVED_NAMES:
                raise ValueError("Access to Windows reserved device names is prohibited")

    validated_path: Path | None = None

    # 3. Resolve and verify boundaries against each allowed root
    for root in allowed_roots:
        try:
            resolved_root = root.resolve(strict=True)
            # Combine the resolved root and user path, then resolve strictly to resolve symlinks
            combined = resolved_root / user_path
            resolved_combined = combined.resolve(strict=True)

            # Native pathlib path-aware boundary check
            if resolved_combined.is_relative_to(resolved_root):
                validated_path = resolved_combined
                break
        except FileNotFoundError:
            # Continue checking other roots, or we will raise FileNotFoundError below
            continue

    if validated_path is None:
        # If we didn't find a valid matching resolved path, either it is out of bounds
        # or the target file does not exist. Let's do a proactive check to see if the combined
        # path exists under any root but was rejected (traversal/symlink escape).
        for root in allowed_roots:
            try:
                resolved_root = root.resolve(strict=True)
                combined = resolved_root / user_path
                # If we resolve with strict=False, does it escape?
                resolved_combined = combined.resolve(strict=False)
                if not resolved_combined.is_relative_to(resolved_root):
                    raise ValueError("Access denied: path traversal or symlink escape detected")
            except Exception:  # noqa: S110
                pass
        raise FileNotFoundError(f"Log file not found or access denied: {user_path}")

    # 4. Enforce that the target must be a file (not a directory or special device)
    if not validated_path.is_file():
        raise ValueError("Target path is not a file")

    return validated_path
