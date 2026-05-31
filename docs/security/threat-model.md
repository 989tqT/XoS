# Threat Model

High-level risks for agent-mediated OS access. Full mitigations land in Phase 1.4+.

| ID | Threat | STRIDE | Mitigation |
|----|--------|--------|------------|
| A | Denylist bypass (`&&`, Unicode, etc.) | Elevation | **Allowlist `op`**; no raw command strings |
| B | Read outside intent (`/etc/shadow`) | Disclosure | Path allowlist + resolve under roots |
| C | Prompt injection in log content | Spoofing | Treat `data` as untrusted; mask secrets |
| D | Dry-run vs execute mismatch | Elevation | Single `build_plan()` path (Phase 3) |
| E | Huge JSON / deep parse DoS | DoS | `XOS_MAX_STDIN_BYTES`, size caps |
| F | Container false sense of safety | Elevation | Document volume/mount least privilege |
| G | Symlink Hijacking / TOCTOU | Elevation | `os.O_NOFOLLOW` write flags, recursive parent `lstat()` checks, and Windows `0x400` junction audits |
| H | Self-Modification | Elevation | Strict **Integrity Denylist** check on resolved canonical paths |
| I | Disk Space Exhaustion | DoS | `shutil.disk_usage` space limit (100MB) & recursive allowlist folder quota limit (50MB) |
| J | Session Scratchpad Directory Traversal | Disclosure / Elevation | Strict path resolution against verified scratchpad boundaries. |
| K | Session Capacity Exhaustion DoS | DoS | Global active session limit cap (< 50 active sessions). Handshake triggers lazy GC to free slots. |
| L | Concurrency Race in Session Purges | Elevation / Tampering | SQLite transactional session deletion first (exclusively claims deletion rights) before filesystem deletes. |
| M | Database Locking / Contention Flooding | DoS | Connect with high SQLite timeout (`30.0s`) and high-performance WAL (Write-Ahead Logging) + Normal Sync settings. |

## CI detection

| Tool | Scope |
|------|--------|
| `bandit` | Python SAST on `src/` |
| `pip-audit` | Known CVEs in dependencies |
| `ruff` S rules | Common insecure patterns |

See [development/ci.md](../development/ci.md).
