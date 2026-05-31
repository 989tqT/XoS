# Agent API (CLI)

Entry point: **`xos invoke`**. Pipe JSON on **stdin** (preferred) or pass **`--request-json`** for local debugging.

## Operations

| `op` | Description | Schema | Execution |
|------|-------------|--------|-----------|
| `health` | Liveness and runtime metadata | `HealthRequest` | Done |
| `handshake` | Initiate secure session scratchpad lease | `HandshakeRequest` | Done (Phase 1.6) |
| `cleanup` | Exclusively purge session files & metadata | `CleanupRequest` | Done (Phase 1.6) |
| `read_log` | Read bytes from allowlisted log path | `ReadLogRequest` | Done (Phase 1.4) |
| `write_file` | Write content to a file under allowed root | `WriteFileRequest` | Done (Phase 1.5) |

---

## `health`

**Request**

```json
{ "op": "health" }
```

**Success `data`**

```json
{
  "status": "ok",
  "platform": "Windows",
  "platform_release": "11",
  "platform_version": "...",
  "python_version": "3.12.3",
  "python_implementation": "CPython",
  "executable": "C:\\...\\python.exe",
  "cli_version": "0.0.1"
}
```

No shell is spawned. Hostname and network probes are intentionally omitted.

---

## `handshake`

**Request**

```json
{
  "op": "handshake",
  "session_id": "90b21703-a26b-4e89-be26-5b4cf5d3a5bb",
  "ttl_seconds": 3600
}
```

| Field | Constraints | Description |
|-------|-------------|-------------|
| `session_id` | `UUID`; optional | Custom session ID. Generated automatically if omitted. |
| `ttl_seconds` | `int`; `60` ... `86400` (default `3600`) | Session lease lifetime before automatic garbage collection. |

**Success `data`**

```json
{
  "session_id": "90b21703-a26b-4e89-be26-5b4cf5d3a5bb",
  "scratchpad": "C:\\Users\\TQT\\.gemini\\antigravity\\sessions\\90b21703-a26b-4e89-be26-5b4cf5d3a5bb\\scratchpad",
  "status": "active"
}
```

*Note: Creates a directory locked to the invoking user (`0o700` permissions on POSIX hosts) and registers metadata.*

---

## `cleanup`

**Request**

```json
{
  "op": "cleanup",
  "session_id": "90b21703-a26b-4e89-be26-5b4cf5d3a5bb"
}
```

| Field | Constraints | Description |
|-------|-------------|-------------|
| `session_id` | `UUID`; required | The active session ID to exclusively terminate and wipe. |

**Success `data`**

```json
{
  "session_id": "90b21703-a26b-4e89-be26-5b4cf5d3a5bb",
  "status": "cleaned"
}
```

---

## `read_log`

**Request**

```json
{
  "op": "read_log",
  "path": "temp.txt",
  "max_bytes": 65536,
  "session_id": "90b21703-a26b-4e89-be26-5b4cf5d3a5bb"
}
```

| Field | Constraints | Description |
|-------|-------------|-------------|
| `path` | `pathlib.Path`; no NUL bytes | Path target; must fall under allowlisted roots or target the session's active scratchpad folder. |
| `max_bytes` | `1` … `1_048_576` (default `65536`) | Maximum line-by-line bytes returned. |
| `session_id` | `UUID`; optional | The active session ID to dynamically allowlist the dynamic scratchpad folder. |

---

## `write_file`

**Request**

```json
{
  "op": "write_file",
  "path": "sandbox/output.txt",
  "content": "Hello, world!",
  "session_id": "90b21703-a26b-4e89-be26-5b4cf5d3a5bb"
}
```

| Field | Constraints | Description |
|-------|-------------|-------------|
| `path` | `pathlib.Path`; no NUL bytes | Target destination; must fall under allowlisted roots or session's active scratchpad. |
| `content` | `string`; max length `1,048,576` | Payload length restriction (1MB cap). |
| `session_id` | `UUID`; optional | Active session ID for dynamic allowed roots appending. |

**Success `data`**

```json
{
  "path": "sandbox/output.txt",
  "resolved_path": "O:\\prj\\p01\\.wip\\XoS\\sandbox\\output.txt",
  "bytes_written": 13,
  "status": "success"
}
```

---

## Error codes (ingress and execution)

| Code | Meaning |
|------|---------|
| `EMPTY_PAYLOAD` | No stdin / empty body |
| `INVALID_JSON` | JSON parse failure |
| `VALIDATION_ERROR` | Pydantic schema rejection |
| `PAYLOAD_TOO_LARGE` | Exceeds `XOS_MAX_STDIN_BYTES` |
| `REQUEST_FILE_NOT_FOUND` | `--request-json` debug path missing |
| `FILE_NOT_FOUND` | Path target or parent directory does not exist (enforces directory existence rule) |
| `ACCESS_DENIED` | Path traversal, symlink hijacking, NTFS junction points, integrity denylist block, or invalid/expired session triggered |
| `DISK_EXHAUSTION` | Destination partition free space is under 100MB |
| `QUOTA_EXCEEDED` | Active session cap exceeded (50 max) or root directory exceeds 50MB quota cap |
| `WRITE_ERROR` | Operating system error encountered during secure database registration or file writing |
