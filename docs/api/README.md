# Agent API (CLI)

Entry point: **`aletheia invoke`**. Pipe JSON on **stdin** (preferred) or pass **`--request-json`** for local debugging.

## Operations

| `op` | Description | Schema | Execution |
|------|-------------|--------|-----------|
| `health` | Liveness and runtime metadata | `HealthRequest` | Done |
| `read_log` | Read bytes from allowlisted log path | `ReadLogRequest` | Done (Phase 1.4) |
| `write_file` | Write content to a file under allowed root | `WriteFileRequest` | Done (Phase 1.5) |

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

## `read_log`

**Request**

```json
{
  "op": "read_log",
  "path": "/var/log/example.log",
  "max_bytes": 65536
}
```

| Field | Constraints |
|-------|-------------|
| `path` | `pathlib.Path`; no NUL bytes; must fall under `ALETHEIA_ALLOWED_ROOTS` (Phase 1.4) |
| `max_bytes` | `1` … `1_048_576` (default `65536`) |

**Current behavior:** Returns `{ ok: true, data: { ... } }` containing the masked file contents wrapped inside a protective CDATA envelope. If validation fails, returns structural errors.

## `write_file`

**Request**

```json
{
  "op": "write_file",
  "path": "sandbox/output.txt",
  "content": "Hello, world!"
}
```

| Field | Constraints |
|-------|-------------|
| `path` | `pathlib.Path`; no NUL bytes; must resolve strictly under `ALETHEIA_ALLOWED_ROOTS` (Phase 1.5) |
| `content` | `string`; max payload length `1,048,576` characters (1MB) (Phase 1.5) |

**Success `data`**

```json
{
  "path": "sandbox/output.txt",
  "resolved_path": "O:\\prj\\p01\\.wip\\aletheia-cli\\sandbox\\output.txt",
  "bytes_written": 13,
  "status": "success"
}
```

## Error codes (ingress and execution)

| Code | Meaning |
|------|---------|
| `EMPTY_PAYLOAD` | No stdin / empty body |
| `INVALID_JSON` | JSON parse failure |
| `VALIDATION_ERROR` | Pydantic schema rejection |
| `PAYLOAD_TOO_LARGE` | Exceeds `ALETHEIA_MAX_STDIN_BYTES` |
| `REQUEST_FILE_NOT_FOUND` | `--request-json` debug path missing |
| `FILE_NOT_FOUND` | Path target or parent directory does not exist (enforces directory existence rule) |
| `ACCESS_DENIED` | Path traversal, symlink hijacking, NTFS junction points, or integrity denylist block triggered |
| `DISK_EXHAUSTION` | Destination partition free space is under 100MB |
| `QUOTA_EXCEEDED` | Projected size of the target allowlisted root directory exceeds 50MB quota cap |
| `WRITE_ERROR` | Operating system error encountered during secure file writing |
