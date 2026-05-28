# Agent API (CLI)

Entry point: **`aletheia invoke`**. Pipe JSON on **stdin** (preferred) or pass **`--request-json`** for local debugging.

## Operations

| `op` | Description | Schema | Execution |
|------|-------------|--------|-----------|
| `health` | Liveness and runtime metadata | `HealthRequest` | Planned (Phase 1.3) |
| `read_log` | Read bytes from allowlisted log path | `ReadLogRequest` | Planned (Phase 1.4) |

## Current `invoke` behavior (Phase 1.2)

Valid requests return HTTP-neutral JSON on stdout:

```json
{
  "ok": true,
  "data": {
    "accepted": true,
    "op": "health",
    "execution": "pending"
  },
  "meta": {
    "trace_id": "<uuid>",
    "command": "health",
    "dry_run": false,
    "version": "0.0.1"
  },
  "errors": []
}
```

Invalid JSON, schema, or missing body → `ok: false` with `errors[].code` such as `INVALID_JSON`, `VALIDATION_ERROR`, `EMPTY_PAYLOAD`.

## `health` (planned response `data`)

**Request**

```json
{ "op": "health" }
```

**Target `data` (Phase 1.3)**

```json
{ "status": "ok", "platform": "..." }
```

## `read_log` (planned)

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
| `path` | `pathlib.Path`; no NUL bytes; must fall under `ALETHEIA_ALLOWED_ROOTS` |
| `max_bytes` | `1` … `1_048_576` (default `65536`) |

**Target `data` (Phase 1.4):** masked log content and metadata (size, path basename only where policy requires).
