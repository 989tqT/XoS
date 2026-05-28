# Agent API (CLI)

Entry point: **`aletheia invoke`**. Pipe JSON on **stdin** (preferred) or pass **`--request-json`** for local debugging.

## Operations

| `op` | Description | Schema | Execution |
|------|-------------|--------|-----------|
| `health` | Liveness and runtime metadata | `HealthRequest` | Done |
| `read_log` | Read bytes from allowlisted log path | `ReadLogRequest` | Planned (Phase 1.4) |

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

**Current behavior:** `ok: false`, `errors[].code` = `NOT_IMPLEMENTED`.

## Error codes (ingress and execution)

| Code | Meaning |
|------|---------|
| `EMPTY_PAYLOAD` | No stdin / empty body |
| `INVALID_JSON` | JSON parse failure |
| `VALIDATION_ERROR` | Pydantic schema rejection |
| `PAYLOAD_TOO_LARGE` | Exceeds `ALETHEIA_MAX_STDIN_BYTES` |
| `REQUEST_FILE_NOT_FOUND` | `--request-json` path missing |
| `NOT_IMPLEMENTED` | Valid `op` not yet executed (`read_log`) |
